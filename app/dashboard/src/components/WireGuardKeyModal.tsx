import {
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
import { ArrowPathIcon, GlobeAltIcon } from "@heroicons/react/24/outline";
import { useCoreSettings, WireGuardKeyPair } from "contexts/CoreSettingsContext";
import { FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { CopyField } from "./CopyField";
import { Icon } from "./Icon";

const ModalIcon = chakra(GlobeAltIcon, {
  baseStyle: { w: 5, h: 5 },
});
const ReloadIcon = chakra(ArrowPathIcon, {
  baseStyle: { w: 4, h: 4 },
});

export const WireGuardKeyButton: FC = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { generateWireGuardKeys } = useCoreSettings();
  const { t } = useTranslation();
  const [keys, setKeys] = useState<WireGuardKeyPair | null>(null);
  const [isLoading, setLoading] = useState(false);

  const generate = () => {
    setLoading(true);
    generateWireGuardKeys()
      .then(setKeys)
      .finally(() => setLoading(false));
  };

  const handleOpen = () => {
    onOpen();
    if (!keys) generate();
  };

  return (
    <>
      <Tooltip label={t("wireguardKey.generate")} placement="top">
        <IconButton
          size="sm"
          variant="outline"
          aria-label="generate wireguard server key"
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
                {t("wireguardKey.title")}
              </Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody pb={6}>
            <Text fontSize="sm" opacity={0.8} mb={4}>
              {t("wireguardKey.description")}
            </Text>
            {isLoading && (
              <HStack justifyContent="center" py={6}>
                <Spinner size="sm" />
              </HStack>
            )}
            {!isLoading && keys && (
              <VStack gap={4} alignItems="flex-start">
                <CopyField label={t("wireguardKey.privateKey")} value={keys.private_key} />
                <CopyField label={t("wireguardKey.publicKey")} value={keys.public_key} />
                <Button
                  size="sm"
                  w="full"
                  leftIcon={<ReloadIcon />}
                  onClick={generate}
                >
                  {t("wireguardKey.regenerate")}
                </Button>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
