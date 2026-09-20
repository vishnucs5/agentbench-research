import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface MetricCardProps {
  title: string
  value: string | number
  description?: string
  accent?: boolean
}

export default function MetricCard({ title, value, description, accent }: MetricCardProps) {
  return (
    <Card
      className={cn(
        "bg-[#101A26] border-[#1E293B] p-5",
        accent && "border-l-[#CFFF4B] border-l-4"
      )}
    >
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-2">
        {title}
      </p>
      <p className="font-mono text-3xl font-bold text-white">{value}</p>
      {description && (
        <p className="mt-2 text-sm text-[#64748B]">{description}</p>
      )}
    </Card>
  )
}
