import {
  Box,
  Button,
  chakra,
  HStack,
  IconButton,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Spinner,
  Text,
  Tooltip,
  useDisclosure,
  VStack,
} from "@chakra-ui/react";
import {
  ArrowPathIcon,
  CheckIcon,
  ClipboardIcon,
  KeyIcon,
} from "@heroicons/react/24/outline";
import {
  useCoreSettings,
  VlessEncKeyPair,
  VlessEncKeys,
} from "contexts/CoreSettingsContext";
import { FC, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";
import { Icon } from "./Icon";

const ModalIcon = chakra(KeyIcon, {
  baseStyle: { w: 5, h: 5 },
});
const ReloadIcon = chakra(ArrowPathIcon, {
  baseStyle: { w: 4, h: 4 },
});
const CopyIcon = chakra(ClipboardIcon, {
  baseStyle: { w: 4, h: 4 },
});
const CopiedIcon = chakra(CheckIcon, {
  baseStyle: { w: 4, h: 4 },
});

const CopyField: FC<{ label: string; value: string }> = ({ label, value }) => {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  return (
    <Box w="full">
      <Text fontSize="xs" fontWeight="medium" color="gray.600" _dark={{ color: "gray.400" }} mb={1}>
        {label}
      </Text>
      <HStack
        border="1px solid"
        borderColor="gray.200"
        _dark={{ borderColor: "gray.600", bg: "gray.700" }}
        bg="gray.50"
        borderRadius="md"
        p={2}
        alignItems="flex-start"
      >
        <Text
          fontSize="xs"
          fontFamily="mono"
          wordBreak="break-all"
          flex="1"
          userSelect="all"
        >
          {value}
        </Text>
        <CopyToClipboard text={value} onCopy={() => setCopied(true)}>
          <div>
            <Tooltip label={copied ? t("vlessEnc.copied") : t("vlessEnc.copy")} placement="top">
              <IconButton
                aria-label="copy"
                size="xs"
                variant="ghost"
                onClick={() => setTimeout(() => setCopied(false), 1000)}
              >
                {copied ? <CopiedIcon /> : <CopyIcon />}
              </IconButton>
            </Tooltip>
          </div>
        </CopyToClipboard>
      </HStack>
    </Box>
  );
};

const KeyPairSection: FC<{ title: string; description: string; pair?: VlessEncKeyPair }> = ({
  title,
  description,
  pair,
}) => {
  const { t } = useTranslation();
  if (!pair) return null;

  return (
    <VStack alignItems="flex-start" w="full" gap={2}>
      <Text fontWeight="semibold" fontSize="sm">
        {title}
      </Text>
      <Text fontSize="xs" opacity={0.7}>
        {description}
      </Text>
      <CopyField label={t("vlessEnc.decryption")} value={pair.decryption} />
      <CopyField label={t("vlessEnc.encryption")} value={pair.encryption} />
    </VStack>
  );
};

export const VlessEncButton: FC = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { generateVlessEncKeys } = useCoreSettings();
  const { t } = useTranslation();
  const [keys, setKeys] = useState<VlessEncKeys | null>(null);
  const [isLoading, setLoading] = useState(false);

  const generate = () => {
    setLoading(true);
    generateVlessEncKeys()
      .then(setKeys)
      .finally(() => setLoading(false));
  };

  const handleOpen = () => {
    onOpen();
    if (!keys) generate();
  };

  return (
    <>
      <Tooltip label={t("vlessEnc.generate")} placement="top">
        <IconButton
          size="sm"
          variant="outline"
          aria-label="generate vless encryption keys"
          onClick={handleOpen}
        >
          <ModalIcon />
        </IconButton>
      </Tooltip>
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
        <ModalContent mx="3">
          <ModalHeader pt={6}>
            <HStack gap={2}>
              <Icon color="primary">
                <ModalIcon color="white" />
              </Icon>
              <Text fontWeight="semibold" fontSize="lg">
                {t("vlessEnc.title")}
              </Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody pb={6}>
            <Text fontSize="sm" opacity={0.8} mb={4}>
              {t("vlessEnc.description")}
            </Text>
            {isLoading && (
              <HStack justifyContent="center" py={6}>
                <Spinner size="sm" />
              </HStack>
            )}
            {!isLoading && keys && (
              <VStack gap={5} alignItems="flex-start">
                <KeyPairSection
                  title={t("vlessEnc.x25519")}
                  description={t("vlessEnc.x25519Desc")}
                  pair={keys.x25519}
                />
                <KeyPairSection
                  title={t("vlessEnc.mlkem768")}
                  description={t("vlessEnc.mlkem768Desc")}
                  pair={keys.mlkem768}
                />
                <Button
                  size="sm"
                  w="full"
                  leftIcon={<ReloadIcon />}
                  onClick={generate}
                >
                  {t("vlessEnc.regenerate")}
                </Button>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
