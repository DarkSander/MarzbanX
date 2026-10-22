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
import { ArrowPathIcon, LockClosedIcon } from "@heroicons/react/24/outline";
import { SS2022Keys, useCoreSettings } from "contexts/CoreSettingsContext";
import { FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { CopyField } from "./CopyField";
import { Icon } from "./Icon";

const ModalIcon = chakra(LockClosedIcon, {
  baseStyle: { w: 5, h: 5 },
});
const ReloadIcon = chakra(ArrowPathIcon, {
  baseStyle: { w: 4, h: 4 },
});

export const SS2022KeyButton: FC = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { generateSS2022Keys } = useCoreSettings();
  const { t } = useTranslation();
  const [keys, setKeys] = useState<SS2022Keys | null>(null);
  const [isLoading, setLoading] = useState(false);

  const generate = () => {
    setLoading(true);
    generateSS2022Keys()
      .then(setKeys)
      .finally(() => setLoading(false));
  };

  const handleOpen = () => {
    onOpen();
    if (!keys) generate();
  };

  return (
    <>
      <Tooltip label={t("ss2022Key.generate")} placement="top">
        <IconButton
          size="sm"
          variant="outline"
          aria-label="generate shadowsocks 2022 server key"
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
                {t("ss2022Key.title")}
              </Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody pb={6}>
            <Text fontSize="sm" opacity={0.8} mb={4}>
              {t("ss2022Key.description")}
            </Text>
            {isLoading && (
              <HStack justifyContent="center" py={6}>
                <Spinner size="sm" />
              </HStack>
            )}
            {!isLoading && keys && (
              <VStack gap={4} alignItems="flex-start">
                {Object.entries(keys).map(([method, key]) => (
                  <CopyField key={method} label={method} value={key} />
                ))}
                <Button
                  size="sm"
                  w="full"
                  leftIcon={<ReloadIcon />}
                  onClick={generate}
                >
                  {t("ss2022Key.regenerate")}
                </Button>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
