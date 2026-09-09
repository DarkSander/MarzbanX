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
import { DocumentCheckIcon } from "@heroicons/react/24/outline";
import { SelfSignedCert, useCoreSettings } from "contexts/CoreSettingsContext";
import { FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { CopyField } from "./CopyField";
import { Icon } from "./Icon";
import { Input } from "./Input";

const ModalIcon = chakra(DocumentCheckIcon, {
  baseStyle: { w: 5, h: 5 },
});

export const SelfSignedCertButton: FC = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { generateSelfSignedCert } = useCoreSettings();
  const { t } = useTranslation();
  const [domain, setDomain] = useState("example.com");
  const [cert, setCert] = useState<SelfSignedCert | null>(null);
  const [isLoading, setLoading] = useState(false);

  const generate = () => {
    if (!domain) return;
    setLoading(true);
    generateSelfSignedCert(domain)
      .then(setCert)
      .finally(() => setLoading(false));
  };

  return (
    <>
      <Tooltip label={t("selfSignedCert.generate")} placement="top">
        <IconButton
          size="sm"
          variant="outline"
          aria-label="generate self-signed certificate"
          onClick={onOpen}
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
                {t("selfSignedCert.title")}
              </Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody pb={6}>
            <Text fontSize="sm" opacity={0.8} mb={4}>
              {t("selfSignedCert.description")}
            </Text>
            <VStack gap={4} alignItems="flex-start">
              <HStack w="full" alignItems="flex-end">
                <Input
                  label={t("selfSignedCert.domain")}
                  size="sm"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="example.com"
                />
                <Button
                  size="sm"
                  colorScheme="primary"
                  onClick={generate}
                  isLoading={isLoading}
                  isDisabled={!domain}
                >
                  {t("selfSignedCert.generateBtn")}
                </Button>
              </HStack>

              {isLoading && (
                <HStack w="full" justifyContent="center" py={6}>
                  <Spinner size="sm" />
                </HStack>
              )}

              {!isLoading && cert && (
                <>
                  <CopyField
                    label={t("selfSignedCert.certificate")}
                    value={cert.certificate.join("\n")}
                    maxHeight="120px"
                  />
                  <CopyField
                    label={t("selfSignedCert.key")}
                    value={cert.key.join("\n")}
                    maxHeight="120px"
                  />
                  <CopyField
                    label={t("selfSignedCert.readyToPaste")}
                    value={JSON.stringify(
                      { certificate: cert.certificate, key: cert.key },
                      null,
                      2
                    )}
                    maxHeight="160px"
                  />
                </>
              )}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
