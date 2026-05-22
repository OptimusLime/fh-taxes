/** @jsxImportSource preact */
// Placeholder image box — thick-bordered, hatched. Caption tells future-us
// what to drop in. Replace with <img src="..." /> when assets land.

type Props = {
  label: string;
  aspect?: string; // e.g., "16/9", "4/3", "1/1"
  flex?: number;   // CSS flex shorthand if used in a flex container
};

export default function ImageSlot({ label, aspect, flex }: Props) {
  const style: Record<string, string> = {};
  if (aspect) style.aspectRatio = aspect;
  if (flex !== undefined) style.flex = String(flex);
  return (
    <div class="p-image-slot" style={style}>
      <span>{label}</span>
    </div>
  );
}
