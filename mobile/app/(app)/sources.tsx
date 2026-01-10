import { View, Text, Pressable, ScrollView } from "react-native";
import { router } from "expo-router";
import { X, Upload, FileText, Trash2 } from "lucide-react-native";
import * as Haptics from "expo-haptics";
import * as DocumentPicker from "expo-document-picker";
import { MotiView } from "moti";
import { toast } from "sonner-native";
import { useUIStore } from "@/lib/stores/useUIStore";
import { uploadFile, deleteFile } from "@/lib/api";
import { COLORS } from "@/constants";
import { formatFileSize } from "@/lib/utils";

export default function SourcesModal() {
  const { sources, setSources, removeSource, addSource, updateSourceStatus } =
    useUIStore();

  const handleClose = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.back();
  };

  const handleUpload = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          "application/pdf",
          "application/msword",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "text/plain",
          "text/markdown",
        ],
        copyToCacheDirectory: true,
        multiple: true,
      });

      if (result.canceled) return;

      for (const asset of result.assets) {
        const tempId = `temp-${Date.now()}-${Math.random()}`;
        addSource({
          id: tempId,
          name: asset.name,
          type: asset.mimeType || "unknown",
          size: formatFileSize(asset.size || 0),
          uploadedAt: new Date().toISOString(),
          status: "uploading",
        });

        try {
          const response = await uploadFile({
            uri: asset.uri,
            name: asset.name,
            type: asset.mimeType || "application/octet-stream",
          });

          if (response.success && response.file) {
            removeSource(tempId);
            addSource({
              id: response.file.id,
              name: response.file.name,
              type: response.file.type,
              size: response.file.size,
              uploadedAt: response.file.uploadedAt,
              status: "synced",
              contentHash: response.file.contentHash,
            });
            toast.success(`Uploaded ${asset.name}`);
          } else {
            updateSourceStatus(tempId, "error");
            toast.error(`Failed to upload ${asset.name}`);
          }
        } catch (error) {
          console.error("Upload error:", error);
          updateSourceStatus(tempId, "error");
          toast.error(`Failed to upload ${asset.name}`);
        }
      }
    } catch (error) {
      console.error("Document picker error:", error);
      toast.error("Failed to select files");
    }
  };

  const handleDelete = async (id: string | number) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    try {
      await deleteFile(String(id));
      removeSource(id);
      toast.success("File deleted");
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Failed to delete file");
    }
  };

  return (
    <View className="flex-1 bg-void">
      <View className="flex-row items-center justify-between px-4 py-4 border-b border-white/10">
        <Text className="text-xl font-bold text-white">Sources</Text>
        <Pressable
          onPress={handleClose}
          className="p-2 rounded-full active:bg-white/10"
        >
          <X size={24} color={COLORS.textSecondary} />
        </Pressable>
      </View>

      <View className="px-4 py-4">
        <Pressable
          onPress={handleUpload}
          className="flex-row items-center justify-center gap-3 p-4 rounded-xl bg-surface border border-white/10 active:bg-white/10"
        >
          <Upload size={20} color={COLORS.accent} />
          <Text className="text-base font-medium text-white">Upload Files</Text>
        </Pressable>
      </View>

      <ScrollView className="flex-1 px-4" showsVerticalScrollIndicator={false}>
        {sources.length === 0 ? (
          <View className="items-center justify-center py-12">
            <FileText size={48} color="rgba(255,255,255,0.2)" />
            <Text className="text-white/40 text-base mt-4 text-center">
              No files uploaded yet.{"\n"}Upload documents to enable RAG.
            </Text>
          </View>
        ) : (
          sources.map((source, index) => (
            <MotiView
              key={source.id}
              from={{ opacity: 0, translateX: -20 }}
              animate={{ opacity: 1, translateX: 0 }}
              transition={{ type: "timing", duration: 300, delay: index * 50 }}
              className="flex-row items-center gap-3 p-4 mb-2 rounded-xl bg-surface/50 border border-white/5"
            >
              <View className="w-10 h-10 rounded-lg bg-indigo-500/20 items-center justify-center">
                <FileText size={20} color={COLORS.accent} />
              </View>

              <View className="flex-1">
                <Text
                  className="text-sm font-medium text-white"
                  numberOfLines={1}
                >
                  {source.name}
                </Text>
                <Text className="text-xs text-white/50 mt-0.5">
                  {source.size} ·{" "}
                  {source.status === "uploading"
                    ? "Uploading..."
                    : source.status === "error"
                      ? "Error"
                      : "Synced"}
                </Text>
              </View>

              <Pressable
                onPress={() => handleDelete(source.id)}
                className="p-2 rounded-lg active:bg-red-500/20"
              >
                <Trash2 size={18} color="#ef4444" />
              </Pressable>
            </MotiView>
          ))
        )}
      </ScrollView>
    </View>
  );
}
