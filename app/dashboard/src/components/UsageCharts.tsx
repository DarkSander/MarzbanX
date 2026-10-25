import {
  Box,
  Button,
  HStack,
  Table,
  TableContainer,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useColorMode,
  VStack,
} from "@chakra-ui/react";
import { ApexOptions } from "apexcharts";
import { FilterUsageType } from "contexts/DashboardContext";
import {
  fetchTopUsers,
  fetchUserUsageTimeline,
  TopUser,
  UsageTimeline,
} from "contexts/UsageStatsContext";
import dayjs from "dayjs";
import { FC, RefObject, useEffect, useLayoutEffect, useRef, useState } from "react";
import ReactApexChart from "react-apexcharts";
import { useTranslation } from "react-i18next";
import { formatBytes } from "utils/formatByte";

// One series per chart, so one hue: primary.500 on light surfaces, the
// lighter primary.300 on dark ones (primary.500 is under 3:1 on gray.700).
// Text and axes use the gray text tokens, never the bar color.
const chartColors = (dark: boolean) => ({
  bar: dark ? "#618ce9" : "#396fe4",
  text: dark ? "#CBD5E0" : "#2D3748",
  muted: dark ? "#A0AEC0" : "#718096",
  grid: dark ? "#4A5568" : "#E2E8F0",
});

const MAX_BAR_PX = 24;

const bytes = (value: number | string, decimals = 1) =>
  formatBytes(Number(value), decimals) as string;

const useWidth = (ref: RefObject<HTMLDivElement>) => {
  const [width, setWidth] = useState(480);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(entry.contentRect.width)
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);
  return width;
};

// bars never thicker than MAX_BAR_PX: the rest of each slot stays air
const barWidthPercent = (plotWidth: number, bars: number) => {
  const slot = plotWidth / Math.max(bars, 1);
  return `${Math.max(Math.min((MAX_BAR_PX / slot) * 100, 80), 10)}%`;
};

const formatPoint = (date: string, period: "hour" | "day") =>
  dayjs(date).format(period === "hour" ? "DD.MM HH:mm" : "DD.MM.YYYY");

export const UserUsageTimeline: FC<{
  username: string;
  query: FilterUsageType;
}> = ({ username, query }) => {
  const { t } = useTranslation();
  const dark = useColorMode().colorMode === "dark";
  const colors = chartColors(dark);
  const ref = useRef<HTMLDivElement>(null);
  const width = useWidth(ref);
  const [data, setData] = useState<UsageTimeline | null>(null);
  const [loading, setLoading] = useState(false);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchUserUsageTimeline(username, query)
      .then(setData)
      .finally(() => setLoading(false));
  }, [username, JSON.stringify(query)]);

  const points = data?.usages || [];
  const period = data?.period || "day";
  const total = points.reduce((sum, p) => sum + p.used_traffic, 0);
  const peakIndex = points.reduce(
    (best, p, i) => (p.used_traffic > points[best].used_traffic ? i : best),
    0
  );
  const peak = points[peakIndex];

  const options: ApexOptions = {
    chart: {
      type: "bar",
      toolbar: { show: false },
      zoom: { enabled: false },
      animations: { enabled: false },
      background: "transparent",
      fontFamily: "inherit",
    },
    theme: { mode: dark ? "dark" : "light" },
    colors: [colors.bar],
    plotOptions: {
      bar: {
        columnWidth: barWidthPercent(width - 60, points.length),
        borderRadius: 4,
        borderRadiusApplication: "end",
        dataLabels: { position: "top" },
      },
    },
    // only the peak is labelled; the axis and the tooltip carry the rest
    dataLabels: {
      enabled: true,
      offsetY: -20,
      formatter: (value: any, { dataPointIndex }: any) =>
        dataPointIndex === peakIndex && Number(value) > 0 ? bytes(value, 1) : "",
      style: { colors: [colors.text], fontSize: "11px", fontWeight: 500 },
    },
    states: { hover: { filter: { type: "lighten", value: 0.08 } } },
    grid: {
      borderColor: colors.grid,
      strokeDashArray: 0,
      xaxis: { lines: { show: false } },
      yaxis: { lines: { show: true } },
      padding: { top: 8 },
    },
    xaxis: {
      type: "datetime",
      labels: {
        datetimeUTC: false,
        style: { colors: colors.muted, fontSize: "11px" },
      },
      axisBorder: { color: colors.grid },
      axisTicks: { show: false },
      tooltip: { enabled: false },
    },
    yaxis: {
      min: 0,
      tickAmount: 4,
      forceNiceScale: true,
      labels: {
        formatter: (value: number) => bytes(value, 0),
        style: { colors: [colors.muted], fontSize: "11px" },
      },
    },
    tooltip: {
      theme: dark ? "dark" : "light",
      x: { format: period === "hour" ? "dd.MM HH:mm" : "dd.MM.yyyy" },
      y: {
        formatter: (value: number) => bytes(value, 2),
        title: { formatter: () => "" },
      },
      marker: { show: false },
    },
  };

  const series = [
    {
      name: t("usageChart.traffic"),
      data: points.map((p) => ({ x: new Date(p.date).getTime(), y: p.used_traffic })),
    },
  ];

  return (
    <VStack w="full" alignItems="stretch" gap={1}>
      <HStack justifyContent="space-between" flexWrap="wrap" rowGap={1}>
        <Text fontSize="sm" fontWeight="medium">
          {t(period === "hour" ? "usageChart.titleHourly" : "usageChart.titleDaily")}
        </Text>
        {data && (
          <Text fontSize="xs" color={colors.muted}>
            {t("usageChart.total")}: <b>{bytes(total, 2)}</b>
            {peak && peak.used_traffic > 0 && (
              <>
                {" · "}
                {t("usageChart.peak")}: <b>{bytes(peak.used_traffic, 2)}</b> (
                {formatPoint(peak.date, period)})
              </>
            )}
          </Text>
        )}
      </HStack>
      <Box ref={ref} w="full" opacity={loading && data ? 0.5 : 1} transition="opacity .2s">
        {data && total === 0 ? (
          <Text fontSize="sm" color={colors.muted} textAlign="center" py={10}>
            {t("usageChart.noData")}
          </Text>
        ) : (
          <ReactApexChart options={options} series={series} type="bar" height={240} />
        )}
      </Box>
      {data && total > 0 && (
        <>
          <Button size="xs" variant="ghost" alignSelf="flex-end" onClick={() => setShowTable(!showTable)}>
            {t(showTable ? "usageChart.hideTable" : "usageChart.showTable")}
          </Button>
          {showTable && (
            <TableContainer maxH="220px" overflowY="auto" borderWidth="1px" borderRadius="md">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>{t("usageChart.date")}</Th>
                    <Th isNumeric>{t("usageChart.traffic")}</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {points
                    .filter((p) => p.used_traffic > 0)
                    .map((p) => (
                      <Tr key={p.date}>
                        <Td fontSize="xs">{formatPoint(p.date, period)}</Td>
                        <Td fontSize="xs" isNumeric sx={{ fontVariantNumeric: "tabular-nums" }}>
                          {bytes(p.used_traffic, 2)}
                        </Td>
                      </Tr>
                    ))}
                </Tbody>
              </Table>
            </TableContainer>
          )}
        </>
      )}
    </VStack>
  );
};

export const TopUsersChart: FC<{ query: FilterUsageType }> = ({ query }) => {
  const { t } = useTranslation();
  const dark = useColorMode().colorMode === "dark";
  const colors = chartColors(dark);
  const [rows, setRows] = useState<TopUser[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchTopUsers(query, 10)
      .then((data) => setRows(data.usages))
      .finally(() => setLoading(false));
  }, [JSON.stringify(query)]);

  const items = rows || [];
  const options: ApexOptions = {
    chart: {
      type: "bar",
      toolbar: { show: false },
      animations: { enabled: false },
      background: "transparent",
      fontFamily: "inherit",
    },
    theme: { mode: dark ? "dark" : "light" },
    colors: [colors.bar],
    plotOptions: {
      bar: {
        horizontal: true,
        barHeight: `${Math.min((MAX_BAR_PX / 36) * 100, 80)}%`,
        borderRadius: 4,
        borderRadiusApplication: "end",
        dataLabels: { position: "top" },
      },
    },
    // a ranking: every bar carries its value at the tip
    dataLabels: {
      enabled: true,
      offsetX: 48,
      formatter: (value: any) => bytes(value, 1),
      style: { colors: [colors.text], fontSize: "11px", fontWeight: 500 },
    },
    states: { hover: { filter: { type: "lighten", value: 0.08 } } },
    grid: {
      borderColor: colors.grid,
      strokeDashArray: 0,
      xaxis: { lines: { show: true } },
      yaxis: { lines: { show: false } },
      padding: { right: 56 },
    },
    xaxis: {
      categories: items.map((r) => r.username),
      labels: {
        formatter: (value: string) => bytes(value, 0),
        style: { colors: colors.muted, fontSize: "11px" },
      },
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: {
      labels: { style: { colors: [colors.text], fontSize: "12px" }, maxWidth: 160 },
    },
    tooltip: {
      theme: dark ? "dark" : "light",
      y: {
        formatter: (value: number) => bytes(value, 2),
        title: { formatter: () => "" },
      },
      marker: { show: false },
    },
  };

  return (
    <Box w="full" opacity={loading && rows ? 0.5 : 1} transition="opacity .2s">
      {rows && items.length === 0 ? (
        <Text fontSize="sm" color={colors.muted} textAlign="center" py={10}>
          {t("usageChart.noData")}
        </Text>
      ) : (
        <ReactApexChart
          options={options}
          series={[{ name: t("usageChart.traffic"), data: items.map((r) => r.used_traffic) }]}
          type="bar"
          height={Math.max(items.length, 3) * 36 + 60}
        />
      )}
    </Box>
  );
};
