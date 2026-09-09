import atexit
import json
import os
import re
import subprocess
import threading
from collections import deque
from contextlib import contextmanager

from app import logger
from app.xray.config import XRayConfig
from config import DEBUG


class XRayCore:
    def __init__(self,
                 executable_path: str = "/usr/bin/xray",
                 assets_path: str = "/usr/share/xray"):
        self.executable_path = executable_path
        self.assets_path = assets_path

        self.version = self.get_version()
        self.process = None
        self.restarting = False

        self._logs_buffer = deque(maxlen=100)
        self._temp_log_buffers = {}
        self._on_start_funcs = []
        self._on_stop_funcs = []
        self._env = {
            **os.environ,
            "XRAY_LOCATION_ASSET": assets_path
        }

        atexit.register(lambda: self.stop() if self.started else None)

    def get_version(self):
        cmd = [self.executable_path, "version"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        m = re.match(r'^Xray (\d+\.\d+\.\d+)', output)
        if m:
            return m.groups()[0]

    def _run_keypair_cmd(self, subcommand: str, private_key: str = None):
        cmd = [self.executable_path, subcommand]
        if private_key:
            cmd.extend(['-i', private_key])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        # Xray-core >= v25 renamed the CLI labels from "Private key"/"Public key"
        # to "PrivateKey"/"Password (PublicKey)"; match both formats. Used by
        # x25519 (REALITY/VLESS Encryption) and wg (WireGuard) alike.
        private_match = re.search(r'Private ?[Kk]ey:\s*(\S+)', output)
        public_match = re.search(r'Public ?[Kk]ey\)?:\s*(\S+)', output)
        if private_match and public_match:
            return {
                "private_key": private_match.group(1),
                "public_key": public_match.group(1)
            }

    def get_x25519(self, private_key: str = None):
        return self._run_keypair_cmd("x25519", private_key)

    def get_wg_key(self, private_key: str = None):
        return self._run_keypair_cmd("wg", private_key)

    def get_mldsa65(self, seed: str = None):
        cmd = [self.executable_path, "mldsa65"]
        if seed:
            cmd.extend(['-i', seed])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        seed_match = re.search(r'Seed:\s*(\S+)', output)
        verify_match = re.search(r'Verify:\s*(\S+)', output)
        if seed_match and verify_match:
            return {
                "seed": seed_match.group(1),
                "verify": verify_match.group(1)
            }

    def get_reality_keys(self, short_id_count: int = 3):
        x25519 = self.get_x25519()
        if not x25519:
            return None

        result = {
            "private_key": x25519["private_key"],
            "public_key": x25519["public_key"],
            # REALITY shortIds are arbitrary even-length hex strings of up
            # to 8 bytes; 8 bytes (16 hex chars) matches Xray-core's own
            # example configs.
            "short_ids": [os.urandom(8).hex() for _ in range(short_id_count)],
        }

        mldsa65 = self.get_mldsa65()
        if mldsa65:
            result["mldsa65_seed"] = mldsa65["seed"]
            result["mldsa65_verify"] = mldsa65["verify"]

        return result

    def get_self_signed_cert(self, domain: str, expire: str = "8760h"):
        cmd = [self.executable_path, "tls", "cert", f"--domain={domain}", f"--expire={expire}"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        data = json.loads(output)
        return {
            "certificate": data["certificate"],
            "key": data["key"],
        }

    def get_vlessenc(self):
        cmd = [self.executable_path, "vlessenc"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')

        # Output looks like:
        #   Authentication: X25519, not Post-Quantum
        #   "decryption": "mlkem768x25519plus.native.600s.XXXX"
        #   "encryption": "mlkem768x25519plus.native.0rtt.YYYY"
        #
        #   Authentication: ML-KEM-768, Post-Quantum
        #   "decryption": "..."
        #   "encryption": "..."
        result = {}
        for section in re.split(r'(?=Authentication:)', output):
            name_match = re.match(r'Authentication:\s*([^,\n]+)', section)
            decryption_match = re.search(r'"decryption":\s*"([^"]+)"', section)
            encryption_match = re.search(r'"encryption":\s*"([^"]+)"', section)
            if not (name_match and decryption_match and encryption_match):
                continue

            key = 'mlkem768' if 'ML-KEM' in name_match.group(1) else 'x25519'
            result[key] = {
                "decryption": decryption_match.group(1),
                "encryption": encryption_match.group(1),
            }

        return result

    def __capture_process_logs(self):
        def capture_and_debug_log():
            while self.process:
                output = self.process.stdout.readline()
                if output:
                    output = output.strip()
                    self._logs_buffer.append(output)
                    for buf in list(self._temp_log_buffers.values()):
                        buf.append(output)
                    logger.debug(output)

                elif not self.process or self.process.poll() is not None:
                    break

        def capture_only():
            while self.process:
                output = self.process.stdout.readline()
                if output:
                    output = output.strip()
                    self._logs_buffer.append(output)
                    for buf in list(self._temp_log_buffers.values()):
                        buf.append(output)

                elif not self.process or self.process.poll() is not None:
                    break

        if DEBUG:
            threading.Thread(target=capture_and_debug_log).start()
        else:
            threading.Thread(target=capture_only).start()

    @contextmanager
    def get_logs(self):
        buf = deque(self._logs_buffer, maxlen=100)
        buf_id = id(buf)
        try:
            self._temp_log_buffers[buf_id] = buf
            yield buf
        finally:
            del self._temp_log_buffers[buf_id]
            del buf

    @property
    def started(self):
        if not self.process:
            return False

        if self.process.poll() is None:
            return True

        return False

    def start(self, config: XRayConfig):
        if self.started is True:
            raise RuntimeError("Xray is started already")

        if config.get('log', {}).get('logLevel') in ('none', 'error'):
            config['log']['logLevel'] = 'warning'

        cmd = [
            self.executable_path,
            "run",
            '-config',
            'stdin:'
        ]
        self.process = subprocess.Popen(
            cmd,
            env=self._env,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True
        )
        self.process.stdin.write(config.to_json())
        self.process.stdin.flush()
        self.process.stdin.close()
        logger.warning(f"Xray core {self.version} started")

        self.__capture_process_logs()

        # execute on start functions
        for func in self._on_start_funcs:
            threading.Thread(target=func).start()

    def stop(self):
        if not self.started:
            return

        self.process.terminate()
        self.process = None
        logger.warning("Xray core stopped")

        # execute on stop functions
        for func in self._on_stop_funcs:
            threading.Thread(target=func).start()

    def restart(self, config: XRayConfig):
        if self.restarting is True:
            return

        try:
            self.restarting = True
            logger.warning("Restarting Xray core...")
            self.stop()
            self.start(config)
        finally:
            self.restarting = False

    def on_start(self, func: callable):
        self._on_start_funcs.append(func)
        return func

    def on_stop(self, func: callable):
        self._on_stop_funcs.append(func)
        return func
