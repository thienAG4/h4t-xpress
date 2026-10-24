import { Construction } from "lucide-react";

type Props = {
  title: string;
  description?: string;
  phase?: string;
};

/** Placeholder for screens that are scheduled in a later phase (SPEC §10). */
export function ComingSoon({ title, description, phase }: Props) {
  return (
    <div className="grid place-items-center rounded-card border border-dashed border-neutral-300 bg-white px-6 py-16 text-center">
      <Construction className="mb-4 size-10 text-primary-600" aria-hidden />
      <h2 className="text-lg font-semibold">{title}</h2>
      {description && <p className="mt-2 max-w-md text-sm text-neutral-600">{description}</p>}
      {phase && (
        <span className="mt-4 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700">
          {phase}
        </span>
      )}
    </div>
  );
}
