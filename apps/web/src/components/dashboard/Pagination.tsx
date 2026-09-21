import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react"

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between px-2 py-4">
      <div className="text-sm text-[#64748B]">
        Page {currentPage} of {totalPages}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B]"
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B]"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        
        {/* Page numbers */}
        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
          const start = Math.max(1, currentPage - 2)
          const page = start + i
          if (page > totalPages) return null
          return (
            <Button
              key={page}
              variant={page === currentPage ? "default" : "outline"}
              size="sm"
              className={
                page === currentPage
                  ? "bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90"
                  : "border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B]"
              }
              onClick={() => onPageChange(page)}
            >
              {page}
            </Button>
          )
        })}
        
        <Button
          variant="outline"
          size="sm"
          className="border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B]"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B]"
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
