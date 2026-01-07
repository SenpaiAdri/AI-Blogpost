import { Tag } from "@/lib/types";

export default function Tags({ tags }: { tags: Tag[] }) {
  if (!tags?.length) return null;

  return (
    <div className="flex flex-wrap sm:gap-4 gap-2">
      {tags.map((tag: Tag) => (
        <span
          key={tag.id}
          className="text-xs font-medium text-[#E7E7E7] bg-[#2c2c31] border border-[#3e3e44] px-2.5 py-1 rounded-full whitespace-nowrap"
        >
          {tag.name}
        </span>
      ))}
    </div>
  );
}
