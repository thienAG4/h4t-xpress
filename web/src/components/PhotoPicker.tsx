// PhotoPicker - take or choose photos, shrink them in the browser and upload right away
// (proof of delivery BR16, incident evidence). Returns the uploaded file ids.

import { useId, useState } from "react";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { uploadFile } from "@/lib/http";
import { shrinkImage } from "@/lib/image";
import type { UploadedFile } from "@/types";

type Props = {
  label: string;
  value: UploadedFile[];
  onChange: (files: UploadedFile[]) => void;
  max?: number;
  error?: string;
};

export function PhotoPicker({ label, value, onChange, max = 3, error }: Props) {
  const inputId = useId();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function addFiles(list: FileList | null) {
    if (!list?.length) return;
    setUploading(true);
    setUploadError(null);
    const added: UploadedFile[] = [];
    try {
      for (const file of Array.from(list).slice(0, max - value.length)) {
        const blob = await shrinkImage(file);
        const name = blob === file ? file.name : file.name.replace(/\.\w+$/, "") + ".jpg";
        added.push(await uploadFile<UploadedFile>("/files", blob, name));
      }
    } catch (failure) {
      setUploadError(errorMessage(failure));
    } finally {
      setUploading(false);
      if (added.length) onChange([...value, ...added]);
    }
  }

  const message = uploadError ?? error;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-ink">{label}</p>
      <div className="grid grid-cols-3 gap-2">
        {value.map((file) => (
          <figure key={file.id} className="relative overflow-hidden rounded-input border border-line bg-white">
            <img src={file.url} alt="Uploaded evidence" className="aspect-square w-full object-cover" />
            <button
              type="button"
              onClick={() => onChange(value.filter((item) => item.id !== file.id))}
              className="absolute inset-x-0 bottom-0 bg-neutral-900/60 py-1 text-xs font-semibold text-white"
            >
              Remove
            </button>
          </figure>
        ))}
        {value.length < max && (
          <label
            htmlFor={inputId}
            className={cn(
              "flex aspect-square cursor-pointer flex-col items-center justify-center rounded-input border border-dashed",
              "bg-white px-2 text-center text-xs font-semibold text-primary-600",
              message ? "border-danger-500" : "border-primary-200",
              uploading && "pointer-events-none opacity-60",
            )}
          >
            {uploading ? "Uploading..." : "Add photo"}
            <span className="mt-1 font-normal text-neutral-500">Camera or gallery</span>
          </label>
        )}
      </div>
      <input
        id={inputId}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="sr-only"
        onChange={(event) => {
          void addFiles(event.target.files);
          event.target.value = "";
        }}
      />
      {message && <p className="text-xs text-danger-500">{message}</p>}
    </div>
  );
}
