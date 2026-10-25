import {
  Badge,
  FormControl,
  FormErrorMessage,
  FormHelperText,
  FormLabel,
  HStack,
  Input,
  Text,
  VStack,
} from "@chakra-ui/react";
import { fetchUserDevices, UserDevices } from "contexts/UsageStatsContext";
import dayjs from "dayjs";
import { FC, useEffect, useState } from "react";
import { useFormContext } from "react-hook-form";
import { useTranslation } from "react-i18next";

// Device limit field, plus the devices the user is online from right now
// when an existing user is open.
export const UserDevicesSection: FC<{ username?: string; disabled?: boolean }> = ({
  username,
  disabled,
}) => {
  const { t } = useTranslation();
  const form = useFormContext();
  const [info, setInfo] = useState<UserDevices | null>(null);

  useEffect(() => {
    setInfo(null);
    if (!username) return;
    fetchUserDevices(username).then(setInfo).catch(() => setInfo(null));
  }, [username]);

  const count = info?.devices.length || 0;
  const over = !!info && info.limit > 0 && count > info.limit;

  return (
    <FormControl mb="10px" isInvalid={!!form.formState.errors.device_limit}>
      <FormLabel>{t("userDialog.deviceLimit")}</FormLabel>
      <Input
        size="sm"
        borderRadius="6px"
        type="number"
        min={0}
        disabled={disabled}
        placeholder={
          info
            ? t("userDialog.deviceLimitDefault", { count: info.default_limit })
            : t("userDialog.deviceLimitDefaultShort")
        }
        {...form.register("device_limit")}
      />
      <FormHelperText fontSize="xs">{t("userDialog.deviceLimitHint")}</FormHelperText>
      <FormErrorMessage>
        {form.formState.errors?.device_limit?.message as string}
      </FormErrorMessage>
      {info && (
        <VStack alignItems="flex-start" gap={1} mt={2}>
          <HStack>
            <Text fontSize="sm">{t("userDialog.devicesOnline")}:</Text>
            <Badge colorScheme={over ? "red" : count ? "green" : "gray"}>
              {info.limit > 0 ? `${count} / ${info.limit}` : `${count} (${t("userDialog.devicesUnlimited")})`}
            </Badge>
          </HStack>
          {info.devices.map((device) => (
            <Text key={device.address} fontSize="xs" opacity={0.8} sx={{ fontVariantNumeric: "tabular-nums" }}>
              {device.address} · {t("userDialog.deviceSince")} {dayjs(device.since).format("DD.MM HH:mm")}
            </Text>
          ))}
        </VStack>
      )}
    </FormControl>
  );
};
