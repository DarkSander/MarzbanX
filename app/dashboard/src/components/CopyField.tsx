import { Box, chakra, HStack, IconButton, Text, Tooltip } from "@chakra-ui/react";
import { CheckIcon, ClipboardIcon } from "@heroicons/react/24/outline";
import { FC, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";

const CopyIcon = chakra(ClipboardIcon, {
  baseStyle: { w: 4, h: 4 },
});
const CopiedIcon = chakra(CheckIcon, {
  baseStyle: { w: 4, h: 4 },
});

export const CopyField: FC<{ label: string; value: string; maxHeight?: string }> = ({
  label,
  value,
  maxHeight,
}) => {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  return (
    <Box w="full">
      {label && (
        <Text fontSize="xs" fontWeight="medium" color="gray.600" _dark={{ color: "gray.400" }} mb={1}>
          {label}
        </Text>
      )}
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
          whiteSpace="pre-wrap"
          wordBreak="break-all"
          flex="1"
          userSelect="all"
          maxHeight={maxHeight}
          overflowY={maxHeight ? "auto" : undefined}
        >
          {value}
        </Text>
        <CopyToClipboard text={value} onCopy={() => setCopied(true)}>
          <div>
            <Tooltip label={copied ? t("copyField.copied") : t("copyField.copy")} placement="top">
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
