import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Checkbox,
  CheckboxGroup,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Spinner,
  Switch,
  Text,
  Tooltip,
  useToast,
  VStack,
  Wrap,
} from "@chakra-ui/react";
import {
  ArrowPathIcon,
  LockClosedIcon,
  PlusIcon as HeroIconPlusIcon,
} from "@heroicons/react/24/outline";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  CertificateFormType,
  CertificateSchema,
  CertificateType,
  FetchCertificatesQueryKey,
  useCertificates,
  useCertificatesQuery,
} from "contexts/CertificatesContext";
import { useDashboard } from "contexts/DashboardContext";
import { FC } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "react-query";
import {
  generateErrorMessage,
  generateSuccessMessage,
} from "utils/toastHandler";
import { chakra } from "@chakra-ui/react";
import { DeleteCertificateModal } from "./DeleteCertificateModal";
import { DeleteIcon } from "./DeleteUserModal";
import { Icon } from "./Icon";
import { Input } from "./Input";

const CustomInput = chakra(Input, {
  baseStyle: {
    bg: "white",
    _dark: {
      bg: "gray.700",
    },
  },
});

const ModalIcon = chakra(LockClosedIcon, {
  baseStyle: { w: 5, h: 5 },
});

const PlusIcon = chakra(HeroIconPlusIcon, {
  baseStyle: { w: 5, h: 5, strokeWidth: 2 },
});

const ReissueIcon = chakra(ArrowPathIcon, {
  baseStyle: { w: 4, h: 4 },
});

const statusColor: Record<CertificateType["status"], string> = {
  issued: "green",
  pending: "blue",
  error: "red",
};

const CertificateAccordion: FC<{ cert: CertificateType }> = ({ cert }) => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { reissueCertificate, setDeletingCertificate } = useCertificates();

  const { isLoading, mutate: reissue } = useMutation(
    reissueCertificate.bind(null, cert),
    {
      onSuccess: () => {
        generateSuccessMessage(
          t("certificates.reissueStarted", { domain: cert.domain }),
          toast
        );
        queryClient.invalidateQueries(FetchCertificatesQueryKey);
      },
      onError: (e) => {
        generateErrorMessage(e, toast);
      },
    }
  );

  const expiringSoon =
    cert.days_remaining !== null && cert.days_remaining <= 14;

  return (
    <AccordionItem
      border="1px solid"
      _dark={{ borderColor: "gray.600" }}
      _light={{ borderColor: "gray.200" }}
      borderRadius="4px"
      p={1}
      w="full"
    >
      <AccordionButton px={2} borderRadius="3px">
        <HStack w="full" justifyContent="space-between" pr={2}>
          <Text
            as="span"
            fontWeight="medium"
            fontSize="sm"
            flex="1"
            textAlign="left"
            color="gray.700"
            _dark={{ color: "gray.300" }}
          >
            {cert.domain}
          </Text>
          <HStack>
            {cert.status === "issued" && cert.days_remaining !== null && (
              <Badge
                colorScheme={expiringSoon ? "orange" : "green"}
                rounded="full"
                px={3}
                py={1}
              >
                <Text fontSize="0.7rem" fontWeight="medium">
                  {t("certificates.daysRemaining", { count: cert.days_remaining })}
                </Text>
              </Badge>
            )}
            <Badge colorScheme={statusColor[cert.status]} rounded="full" px={3} py={1}>
              <Text
                textTransform="capitalize"
                fontSize="0.7rem"
                fontWeight="medium"
              >
                {t(`certificates.status.${cert.status}`)}
              </Text>
            </Badge>
          </HStack>
        </HStack>
        <AccordionIcon />
      </AccordionButton>
      <AccordionPanel px={2} pb={2}>
        <VStack alignItems="flex-start" gap={2} fontSize="sm">
          {cert.status === "error" && cert.last_error && (
            <Alert status="error" size="xs" borderRadius="md">
              <AlertIcon w={4} />
              <Text fontSize="xs">{cert.last_error}</Text>
            </Alert>
          )}
          {cert.expires_at && (
            <Text color="gray.600" _dark={{ color: "gray.400" }}>
              {t("certificates.expiresAt")}: {new Date(cert.expires_at).toLocaleDateString()}
            </Text>
          )}
          <Text color="gray.600" _dark={{ color: "gray.400" }}>
            {t("certificates.autoRenew")}: {cert.auto_renew ? t("certificates.enabled") : t("certificates.disabled")}
          </Text>
          {cert.inbound_tags.length > 0 && (
            <Wrap>
              {cert.inbound_tags.map((tag) => (
                <Badge key={tag} variant="outline" fontSize="0.65rem">
                  {tag}
                </Badge>
              ))}
            </Wrap>
          )}
          <HStack w="full" pt={1}>
            <Tooltip label={t("delete")} placement="top">
              <IconButton
                colorScheme="red"
                variant="ghost"
                size="sm"
                aria-label="delete certificate"
                onClick={() => setDeletingCertificate(cert)}
              >
                <DeleteIcon />
              </IconButton>
            </Tooltip>
            <Button
              flexGrow={1}
              size="sm"
              colorScheme="primary"
              w="full"
              isLoading={isLoading}
              leftIcon={<ReissueIcon />}
              onClick={() => reissue()}
            >
              {t("certificates.reissue")}
            </Button>
          </HStack>
        </VStack>
      </AccordionPanel>
    </AccordionItem>
  );
};

const RequestCertificateForm: FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { inbounds } = useDashboard();
  const { requestCertificate } = useCertificates();

  const tlsInbounds = Array.from(inbounds.values())
    .flat()
    .filter((inbound) => inbound.tls === "tls");

  const form = useForm<CertificateFormType>({
    resolver: zodResolver(CertificateSchema),
    defaultValues: { domain: "", inbound_tags: [], auto_renew: true },
  });

  const { isLoading, mutate } = useMutation(requestCertificate, {
    onSuccess: () => {
      generateSuccessMessage(
        t("certificates.requestStarted", { domain: form.getValues("domain") }),
        toast
      );
      queryClient.invalidateQueries(FetchCertificatesQueryKey);
      form.reset();
    },
    onError: (e) => {
      generateErrorMessage(e, toast, form);
    },
  });

  return (
    <form onSubmit={form.handleSubmit((v) => mutate(v))}>
      <VStack alignItems="flex-start" gap={3}>
        <FormControl>
          <CustomInput
            label={t("certificates.domain")}
            size="sm"
            placeholder="example.com"
            {...form.register("domain")}
            error={form.formState?.errors?.domain?.message}
          />
        </FormControl>

        {tlsInbounds.length > 0 && (
          <FormControl>
            <FormLabel fontSize="sm">{t("certificates.applyToInbounds")}</FormLabel>
            <Controller
              name="inbound_tags"
              control={form.control}
              render={({ field }) => (
                <CheckboxGroup value={field.value} onChange={field.onChange}>
                  <Wrap>
                    {tlsInbounds.map((inbound) => (
                      <Checkbox key={inbound.tag} value={inbound.tag} fontSize="sm">
                        {inbound.tag}
                      </Checkbox>
                    ))}
                  </Wrap>
                </CheckboxGroup>
              )}
            />
          </FormControl>
        )}

        <FormControl display="flex" alignItems="center">
          <FormLabel fontSize="sm" mb="0">
            {t("certificates.autoRenew")}
          </FormLabel>
          <Controller
            name="auto_renew"
            control={form.control}
            render={({ field }) => (
              <Switch
                colorScheme="primary"
                isChecked={field.value}
                onChange={(e) => field.onChange(e.target.checked)}
              />
            )}
          />
        </FormControl>

        <Button
          type="submit"
          colorScheme="primary"
          size="sm"
          px={5}
          w="full"
          isLoading={isLoading}
          leftIcon={<PlusIcon />}
        >
          {t("certificates.request")}
        </Button>
      </VStack>
    </form>
  );
};

export const CertificatesModal: FC = () => {
  const { isEditingCertificates, onEditingCertificates } = useDashboard();
  const { t } = useTranslation();
  const { data: certificates, isLoading } = useCertificatesQuery();

  const onClose = () => onEditingCertificates(false);

  return (
    <>
      <Modal isOpen={isEditingCertificates} onClose={onClose}>
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
        <ModalContent mx="3" w="fit-content" maxW="3xl">
          <ModalHeader pt={6}>
            <Icon color="primary">
              <ModalIcon color="white" />
            </Icon>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody w="440px" pb={6} pt={3}>
            <Text mb={3} opacity={0.8} fontSize="sm">
              {t("certificates.title")}
            </Text>
            {isLoading && <Spinner size="sm" />}

            <Accordion w="full" allowToggle>
              <VStack w="full">
                {!isLoading &&
                  certificates &&
                  certificates.map((cert) => (
                    <CertificateAccordion key={cert.id} cert={cert} />
                  ))}

                <AccordionItem
                  border="1px solid"
                  _dark={{ borderColor: "gray.600" }}
                  _light={{ borderColor: "gray.200" }}
                  borderRadius="4px"
                  p={1}
                  w="full"
                >
                  <AccordionButton px={2} borderRadius="3px">
                    <Text
                      as="span"
                      fontWeight="medium"
                      fontSize="sm"
                      flex="1"
                      textAlign="left"
                      color="gray.700"
                      _dark={{ color: "gray.300" }}
                      display="flex"
                      gap={1}
                    >
                      <PlusIcon display="inline-block" />
                      <span>{t("certificates.requestNew")}</span>
                    </Text>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel px={2} py={4}>
                    <RequestCertificateForm />
                  </AccordionPanel>
                </AccordionItem>
              </VStack>
            </Accordion>
          </ModalBody>
        </ModalContent>
      </Modal>
      <DeleteCertificateModal />
    </>
  );
};
