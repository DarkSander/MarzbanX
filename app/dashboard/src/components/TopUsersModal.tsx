import {
  chakra,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  VStack,
} from "@chakra-ui/react";
import { ChartBarIcon } from "@heroicons/react/24/outline";
import { FilterUsageType, useDashboard } from "contexts/DashboardContext";
import dayjs from "dayjs";
import { FC, useState } from "react";
import { useTranslation } from "react-i18next";
import { Icon } from "./Icon";
import { TopUsersChart } from "./UsageCharts";
import { UsageFilter } from "./UsageFilter";

export const TopUsersIcon = chakra(ChartBarIcon, {
  baseStyle: { w: 5, h: 5 },
});

const defaultQuery = (): FilterUsageType => ({
  start: dayjs().utc().subtract(30, "day").format("YYYY-MM-DDTHH:00:00"),
});

export const TopUsersModal: FC = () => {
  const { isShowingTopUsers, onShowingTopUsers } = useDashboard();
  const { t } = useTranslation();
  const [filter, setFilter] = useState("1m");
  const [query, setQuery] = useState<FilterUsageType>(defaultQuery);

  const onClose = () => {
    onShowingTopUsers(false);
    setFilter("1m");
    setQuery(defaultQuery());
  };

  return (
    <Modal isOpen={isShowingTopUsers} onClose={onClose} size="2xl">
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent mx="3" w="full">
        <ModalHeader pt={6}>
          <HStack gap={2}>
            <Icon color="primary">
              <TopUsersIcon color="white" />
            </Icon>
            <Text fontWeight="semibold" fontSize="lg">
              {t("topUsers.title")}
            </Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton mt={3} />
        <ModalBody pb={6}>
          <VStack gap={4} alignItems="stretch">
            <UsageFilter
              defaultValue={filter}
              onChange={(value, newQuery) => {
                setFilter(value);
                setQuery(newQuery);
              }}
            />
            {isShowingTopUsers && <TopUsersChart query={query} />}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};
