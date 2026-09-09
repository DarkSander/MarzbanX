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
import { ArrowPathIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";
import { RealityKeys, useCoreSettings } from "contexts/CoreSettingsContext";
import { FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { CopyField } from "./CopyField";
import { Icon } from "./Icon";

const ModalIcon = chakra(ShieldCheckIcon, {
  baseStyle: { w: 5, h: 5 },
});
const ReloadIcon = chakra(ArrowPathIcon, {
  baseStyle: { w: 4, h: 4 },
});

export const RealityKeysButton: FC = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { generateRealityKeys } = useCoreSettings();
  const { t } = useTranslation();
  const [keys, setKeys] = useState<RealityKeys | null>(null);
  const [isLoading, setLoading] = useState(false);

  const generate = () => {
    setLoading(true);
    generateRealityKeys(3)
      .then(setKeys)
      .finally(() => setLoading(false));
  };

  const handleOpen = () => {
    onOpen();
    if (!keys) generate();
  };

  return (
    <>
      <Tooltip label={t("realityKeys.generate")} placement="top">
        <IconButton
          size="sm"
          variant="outline"
          aria-label="generate reality keys"
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
                {t("realityKeys.title")}
              </Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody pb={6}>
            <Text fontSize="sm" opacity={0.8} mb={4}>
              {t("realityKeys.description")}
            </Text>
            {isLoading && (
              <HStack justifyContent="center" py={6}>
                <Spinner size="sm" />
              </HStack>
            )}
            {!isLoading && keys && (
              <VStack gap={4} alignItems="flex-start">
                <CopyField label={t("realityKeys.privateKey")} value={keys.private_key} />
                <CopyField label={t("realityKeys.publicKey")} value={keys.public_key} />
                <Text fontSize="xs" fontWeight="medium" color="gray.600" _dark={{ color: "gray.400" }}>
                  {t("realityKeys.shortIds")}
                </Text>
                <VStack w="full" gap={2}>
                  {keys.short_ids.map((sid, i) => (
                    <CopyField
                      key={sid}
                      label={`${t("realityKeys.shortId")} ${i + 1}`}
                      value={sid}
                    />
                  ))}
                </VStack>
                <Button
                  size="sm"
                  w="full"
                  leftIcon={<ReloadIcon />}
                  onClick={generate}
                >
                  {t("realityKeys.regenerate")}
                </Button>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
