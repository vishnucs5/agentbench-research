import { Wifi, WifiOff } from "lucide-react"

interface LiveIndicatorProps {
  isConnected: boolean
}

export default function LiveIndicator({ isConnected }: LiveIndicatorProps) {
  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
      {isConnected ? (
        <>
          <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
          <Wifi className="h-3 w-3 text-green-500" />
          <span>Live</span>
        </>
      ) : (
        <>
          <span className="h-1.5 w-1.5 rounded-full bg-gray-500" />
          <WifiOff className="h-3 w-3 text-gray-500" />
          <span>Offline</span>
        </>
      )}
    </div>
  )
}
