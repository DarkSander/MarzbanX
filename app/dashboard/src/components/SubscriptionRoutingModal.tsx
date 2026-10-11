import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  chakra,
  Divider,
  FormControl,
  FormLabel,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Spinner,
  Switch,
  Text,
  Textarea,
  useToast,
  VStack,
  Wrap,
} from "@chakra-ui/react";
import { ArrowPathIcon, MapIcon } from "@heroicons/react/24/outline";
import { useDashboard } from "contexts/DashboardContext";
import {
  FetchSubscriptionRoutingQueryKey,
  HappRoutingProfile,
  PRESET_SOURCES,
  refreshSubscriptionRouting,
  saveSubscriptionRouting,
  SubscriptionRoutingSource,
  SubscriptionRoutingType,
  useSubscriptionRoutingQuery,
} from "contexts/SubscriptionRoutingContext";
import { FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "react-query";
import { generateErrorMessage, generateSuccessMessage } from "utils/toastHandler";
import { Icon } from "./Icon";

const ModalIcon = chakra(MapIcon, { baseStyle: { w: 5, h: 5 } });
const RefreshIcon = chakra(ArrowPathIcon, { baseStyle: { w: 4, h: 4 } });

const SOURCES: SubscriptionRoutingSource[] = [
  "roscomvpn_default",
  "roscomvpn_whitelist",
  "custom_link",
  "custom_json",
];

const PREVIEW_LISTS: { key: keyof HappRoutingProfile; color: string }[] = [
  { key: "DirectSites", color: "green" },
  { key: "ProxySites", color: "blue" },
  { key: "BlockSites", color: "red" },
];

const ProfilePreview: FC<{ profile: HappRoutingProfile }> = ({ profile }) => {
  const { t } = useTranslation();
  return (
    <VStack alignItems="flex-start" w="full" gap={2}>
      <Text fontSize="sm" fontWeight="semibold">
        {t("subscriptionRouting.preview")}: {profile.Name || "—"}
      </Text>
      {PREVIEW_LISTS.map(({ key, color }) => {
        const items = (profile[key] as string[] | undefined) || [];
        return (
          <Box key={key} w="full">
            <Text fontSize="xs" opacity={0.7} mb={1}>
              {key} ({items.length})
            </Text>
            {items.length > 0 ? (
              <Wrap spacing={1}>
                {items.map((item) => (
                  <Badge key={item} colorScheme={color} variant="subtle" fontSize="0.65rem" textTransform="none">
                    {item}
                  </Badge>
                ))}
              </Wrap>
            ) : (
              <Text fontSize="xs" opacity={0.5}>
                —
              </Text>
            )}
          </Box>
        );
      })}
    </VStack>
  );
};

const SubscriptionRoutingForm: FC<{ data: SubscriptionRoutingType }> = ({ data }) => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();

  const [enabled, setEnabled] = useState(data.enabled);
  const [source, setSource] = useState<SubscriptionRoutingSource>(data.source);
  const [customValue, setCustomValue] = useState(data.custom_value || "");
  const [happOnly, setHappOnly] = useState(data.happ_only);

  useEffect(() => {
    setEnabled(data.enabled);
    setSource(data.source);
    setCustomValue(data.custom_value || "");
    setHappOnly(data.happ_only);
  }, [data]);

  const onSaved = (fresh: SubscriptionRoutingType) =>
    queryClient.setQueryData(FetchSubscriptionRoutingQueryKey, fresh);

  const save = useMutation(saveSubscriptionRouting, {
    onSuccess: (fresh) => {
      onSaved(fresh);
      generateSuccessMessage(t("subscriptionRouting.saved"), toast);
    },
    onError: (e) => {
      generateErrorMessage(e, toast);
    },
  });

  const refresh = useMutation(refreshSubscriptionRouting, {
    onSuccess: (fresh) => {
      onSaved(fresh);
      if (fresh.last_error)
        toast({
          title: `${t("subscriptionRouting.fetchError")}: ${fresh.last_error}`,
          status: "warning",
          isClosable: true,
          position: "top",
          duration: 5000,
        });
      else generateSuccessMessage(t("subscriptionRouting.refreshed"), toast);
    },
    onError: (e) => {
      generateErrorMessage(e, toast);
    },
  });

  const isCustom = source === "custom_link" || source === "custom_json";
  const savedIsPreset = PRESET_SOURCES.includes(data.source);
  const tooLarge = data.link_length !== null && data.link_length > data.max_header_size;

  return (
    <>
      <ModalBody>
        <VStack alignItems="flex-start" gap={4}>
          <Text fontSize="sm" opacity={0.8}>
            {t("subscriptionRouting.description")}
          </Text>

          <FormControl display="flex" alignItems="center">
            <FormLabel fontSize="sm" mb="0" flex="1">
              {t("subscriptionRouting.enabled")}
            </FormLabel>
            <Switch colorScheme="primary" isChecked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          </FormControl>

          <FormControl>
            <FormLabel fontSize="sm">{t("subscriptionRouting.source")}</FormLabel>
            <Select
              size="sm"
              value={source}
              onChange={(e) => setSource(e.target.value as SubscriptionRoutingSource)}
            >
              {SOURCES.map((s) => (
                <option key={s} value={s}>
                  {t(`subscriptionRouting.sources.${s}`)}
                </option>
              ))}
            </Select>
          </FormControl>

          {isCustom && (
            <FormControl>
              <FormLabel fontSize="sm">
                {t(source === "custom_link" ? "subscriptionRouting.customLink" : "subscriptionRouting.customJson")}
              </FormLabel>
              <Textarea
                size="sm"
                fontFamily="mono"
                fontSize="xs"
                rows={source === "custom_json" ? 10 : 4}
                value={customValue}
                placeholder={
                  source === "custom_link" ? "happ://routing/onadd/eyJOYW1lIjoi..." : '{\n  "Name": "My profile",\n  "DirectSites": ["geosite:category-ru"]\n}'
                }
                onChange={(e) => setCustomValue(e.target.value)}
              />
            </FormControl>
          )}

          <FormControl>
            <HStack>
              <FormLabel fontSize="sm" mb="0" flex="1">
                {t("subscriptionRouting.happOnly")}
              </FormLabel>
              <Switch colorScheme="primary" isChecked={happOnly} onChange={(e) => setHappOnly(e.target.checked)} />
            </HStack>
            <Text fontSize="xs" opacity={0.6} mt={1}>
              {t("subscriptionRouting.happOnlyHint")}
            </Text>
          </FormControl>

          <Divider />

          {savedIsPreset && (
            <HStack w="full" justifyContent="space-between">
              <Text fontSize="xs" opacity={0.7}>
                {t("subscriptionRouting.fetchedAt")}:{" "}
                {data.fetched_at ? new Date(data.fetched_at + "Z").toLocaleString() : "—"}
              </Text>
              <Button
                size="xs"
                leftIcon={<RefreshIcon />}
                isLoading={refresh.isLoading}
                onClick={() => refresh.mutate()}
              >
                {t("subscriptionRouting.refreshNow")}
              </Button>
            </HStack>
          )}

          {savedIsPreset && data.last_error && (
            <Alert status="warning" borderRadius="md" fontSize="xs">
              <AlertIcon />
              {t("subscriptionRouting.fetchError")}: {data.last_error}
            </Alert>
          )}

          {data.link_length !== null && (
            <Text fontSize="xs" opacity={0.7}>
              {t("subscriptionRouting.size", { size: data.link_length, max: data.max_header_size })}
            </Text>
          )}
          {tooLarge && (
            <Alert status="error" borderRadius="md" fontSize="xs">
              <AlertIcon />
              {t("subscriptionRouting.tooLarge")}
            </Alert>
          )}

          {data.profile ? (
            <ProfilePreview profile={data.profile} />
          ) : (
            <Text fontSize="xs" opacity={0.6}>
              {t("subscriptionRouting.noProfile")}
            </Text>
          )}
        </VStack>
      </ModalBody>
      <ModalFooter>
        <Button
          size="sm"
          colorScheme="primary"
          w="full"
          isLoading={save.isLoading}
          onClick={() =>
            save.mutate({
              enabled,
              source,
              custom_value: isCustom ? customValue : null,
              happ_only: happOnly,
            })
          }
        >
          {t("subscriptionRouting.save")}
        </Button>
      </ModalFooter>
    </>
  );
};

export const SubscriptionRoutingModal: FC = () => {
  const { isEditingSubscriptionRouting, onEditingSubscriptionRouting } = useDashboard();
  const { t } = useTranslation();
  const { data, isLoading } = useSubscriptionRoutingQuery(isEditingSubscriptionRouting);

  return (
    <Modal
      isOpen={isEditingSubscriptionRouting}
      onClose={() => onEditingSubscriptionRouting(false)}
      size="lg"
      scrollBehavior="inside"
    >
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent mx="3">
        <ModalHeader pt={6}>
          <HStack gap={2}>
            <Icon color="primary">
              <ModalIcon color="white" />
            </Icon>
            <Text fontWeight="semibold" fontSize="lg">
              {t("subscriptionRouting.title")}
            </Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton mt={3} />
        {isLoading || !data ? (
          <ModalBody>
            <HStack justifyContent="center" py={6}>
              <Spinner size="sm" />
            </HStack>
          </ModalBody>
        ) : (
          <SubscriptionRoutingForm data={data} />
        )}
      </ModalContent>
    </Modal>
  );
};
