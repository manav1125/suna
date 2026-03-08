import React, { useMemo, useState, useRef } from 'react';
import { AlertTriangle, Play, Pause, Wand2, Download, Video as VideoIcon, Image as ImageIcon } from 'lucide-react';
import { ToolViewProps } from '../types';
import { extractImageEditGenerateData } from './_utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useImageContent } from '@/hooks/files';
import { useFileContentQuery } from '@/hooks/files/use-file-queries';
import { VideoRenderer } from '@/components/file-renderers/video-renderer';

const BLOB_COLORS = [
  'from-zinc-300/60 to-zinc-400/60',
  'from-zinc-350/60 to-zinc-450/60',
  'from-neutral-300/60 to-neutral-400/60',
  'from-stone-300/60 to-stone-400/60',
  'from-gray-300/60 to-gray-400/60',
  'from-slate-300/60 to-slate-400/60',
];

function ShimmerBox({ aspectVideo = false }: { aspectVideo?: boolean }) {
  // Use ref to store color so it doesn't change on re-renders
  const colorRef = useRef(BLOB_COLORS[Math.floor(Math.random() * BLOB_COLORS.length)]);
  const [showColor, setShowColor] = useState(false);

  // Fade in color after a delay
  React.useEffect(() => {
    const timer = setTimeout(() => setShowColor(true), 800);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className={`relative w-full ${aspectVideo ? 'aspect-video' : 'aspect-square'} rounded-2xl overflow-hidden border border-neutral-200 dark:border-neutral-700/50`}>
      {/* Gray base layer - contained with rounded corners */}
      <div className="absolute inset-[-50%] bg-gradient-to-br from-zinc-300/60 to-zinc-400/60 dark:from-zinc-600/60 dark:to-zinc-700/60 blur-2xl" />
      {/* Color layer that fades in - contained with rounded corners */}
      <div
        className={`absolute inset-[-50%] bg-gradient-to-br ${colorRef.current} blur-2xl transition-opacity duration-1000`}
        style={{ opacity: showColor ? 1 : 0 }}
      />
      <div className="absolute inset-0 bg-zinc-100/30 dark:bg-zinc-900/30 backdrop-blur-sm rounded-2xl" />
      <div
        className="absolute inset-0 rounded-2xl"
        style={{
          background: 'linear-gradient(110deg, transparent 30%, rgba(255,255,255,0.4) 50%, transparent 70%)',
          backgroundSize: '200% 100%',
          animation: 'media-shimmer 1.8s ease-in-out infinite',
        }}
      />
      <style>{`
        @keyframes media-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}

function MediaLoadingState({
  aspectVideo = false,
  progress,
  statusLabel,
  prompt,
}: {
  aspectVideo?: boolean;
  progress: number;
  statusLabel: string;
  prompt?: string | null;
}) {
  return (
    <div className="relative">
      <ShimmerBox aspectVideo={aspectVideo} />
      <div className="absolute inset-0 flex items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-white/40 bg-white/78 p-5 shadow-xl backdrop-blur-md dark:border-zinc-700/80 dark:bg-zinc-950/80">
          <div className="mb-4 flex items-center gap-2">
            <Badge variant="secondary" className="gap-1.5">
              <Wand2 className="h-3.5 w-3.5" />
              Generating
            </Badge>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {statusLabel}
            </p>
            <Progress value={progress} className="h-1.5" />
            <p className="text-xs text-zinc-600 dark:text-zinc-400">
              {Math.round(progress)}% estimated progress
            </p>
            {prompt && (
              <p className="line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
                {prompt}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ImageDisplay({ filePath, sandboxId }: { filePath: string; sandboxId?: string }) {
  const { data: imageUrl, isLoading } = useImageContent(sandboxId, filePath, {
    enabled: !!sandboxId && !!filePath,
  });

  if (isLoading || !imageUrl) {
    return <ShimmerBox />;
  }

  return (
    <img
      src={imageUrl}
      alt={filePath}
      className="w-full rounded-2xl border border-neutral-200 dark:border-neutral-700/50 object-contain"
    />
  );
}

function VideoDisplay({ filePath, sandboxId }: { filePath: string; sandboxId?: string }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isVideoLoading, setIsVideoLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Use the same file content approach that images use - fetch blob with proper auth
  const { data: videoBlob, isLoading: isBlobLoading } = useVideoContent(sandboxId, filePath, {
    enabled: !!sandboxId && !!filePath,
  });

  // Create and manage blob URL
  React.useEffect(() => {
    if (videoBlob instanceof Blob) {
      const newUrl = URL.createObjectURL(videoBlob);
      setVideoUrl(newUrl);

      return () => {
        URL.revokeObjectURL(newUrl);
        setVideoUrl(null);
      };
    } else {
      setVideoUrl(null);
    }
  }, [videoBlob]);

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Show shimmer while loading blob
  if (isBlobLoading || !videoUrl) {
    return <ShimmerBox aspectVideo />;
  }

  if (hasError) {
    return (
      <div className="aspect-video flex flex-col items-center justify-center p-4 text-center rounded-2xl border border-neutral-200 dark:border-neutral-700/50 bg-muted/30">
        <AlertTriangle className="h-8 w-8 text-destructive mb-2" />
        <p className="text-destructive font-medium text-sm">Failed to load video</p>
      </div>
    );
  }

  return (
    <div className="relative rounded-2xl overflow-hidden border border-neutral-200 dark:border-neutral-700/50 bg-black">
      {isVideoLoading && (
        <div className="absolute inset-0 z-10">
          <ShimmerBox aspectVideo />
        </div>
      )}
      <div className="relative group">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full aspect-video object-contain"
          loop
          muted
          playsInline
          onLoadedData={() => setIsVideoLoading(false)}
          onError={() => {
            setHasError(true);
            setIsVideoLoading(false);
          }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />
        {/* Play/Pause overlay */}
        <div
          className="absolute inset-0 flex items-center justify-center cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity bg-black/20"
          onClick={togglePlay}
        >
          <div className="h-14 w-14 rounded-full bg-white/90 dark:bg-black/90 flex items-center justify-center shadow-lg">
            {isPlaying ? (
              <Pause className="h-7 w-7 text-foreground" />
            ) : (
              <Play className="h-7 w-7 text-foreground ml-0.5" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Hook for video content - similar to useImageContent but for video
function useVideoContent(
  sandboxId?: string,
  filePath?: string,
  options: { enabled?: boolean } = {}
) {
  const { data, isLoading, error } = useFileContentQuery(sandboxId, filePath, {
    contentType: 'blob',
    enabled: options.enabled,
    staleTime: 5 * 60 * 1000,
  });

  return { data, isLoading, error };
}

// Full featured video renderer component for tool view (Computer)
// Uses the full VideoRenderer with all controls (slider, volume, etc.)
function VideoRendererFull({ filePath, sandboxId }: { filePath: string; sandboxId?: string }) {
  const [hasVideoError, setHasVideoError] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  // Fetch video blob with proper auth
  const { data: videoBlob, isLoading, error: fetchError } = useVideoContent(sandboxId, filePath, {
    enabled: !!sandboxId && !!filePath,
  });

  // Create and manage blob URL
  React.useEffect(() => {
    if (videoBlob instanceof Blob) {
      console.log('[VideoRendererFull] Creating blob URL for video:', {
        filePath,
        blobSize: videoBlob.size,
        blobType: videoBlob.type,
      });
      const newUrl = URL.createObjectURL(videoBlob);
      console.log('[VideoRendererFull] Created blob URL:', newUrl);
      setVideoUrl(newUrl);

      // Cleanup function to revoke URL when blob changes or component unmounts
      return () => {
        console.log('[VideoRendererFull] Revoking blob URL:', newUrl);
        URL.revokeObjectURL(newUrl);
        setVideoUrl(null);
      };
    } else {
      console.log('[VideoRendererFull] No blob available:', { videoBlob, isLoading, fetchError });
      setVideoUrl(null);
    }
  }, [videoBlob, filePath, isLoading, fetchError]);

  // Show shimmer while loading
  if (isLoading) {
    return <ShimmerBox aspectVideo />;
  }

  // Show error if fetch failed
  if (fetchError || (!videoBlob && !isLoading)) {
    return (
      <div className="aspect-video flex flex-col items-center justify-center p-6 text-center rounded-2xl border border-neutral-200 dark:border-neutral-700/50 bg-muted/30">
        <AlertTriangle className="h-10 w-10 text-zinc-500 dark:text-zinc-400 mb-3" />
        <h3 className="text-base font-medium text-zinc-900 dark:text-zinc-100 mb-2">
          Failed to load video
        </h3>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {fetchError ? String(fetchError) : 'The video could not be loaded'}
        </p>
      </div>
    );
  }

  // Show error if no URL could be created
  if (!videoUrl) {
    return (
      <div className="aspect-video flex flex-col items-center justify-center p-6 text-center rounded-2xl border border-neutral-200 dark:border-neutral-700/50 bg-muted/30">
        <AlertTriangle className="h-10 w-10 text-zinc-500 dark:text-zinc-400 mb-3" />
        <h3 className="text-base font-medium text-zinc-900 dark:text-zinc-100 mb-2">
          Failed to load video
        </h3>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Could not create video URL
        </p>
      </div>
    );
  }

  // Video error handler
  if (hasVideoError) {
    return (
      <div className="aspect-video flex flex-col items-center justify-center p-6 text-center rounded-2xl border border-neutral-200 dark:border-neutral-700/50 bg-muted/30">
        <AlertTriangle className="h-10 w-10 text-zinc-500 dark:text-zinc-400 mb-3" />
        <h3 className="text-base font-medium text-zinc-900 dark:text-zinc-100 mb-2">
          Failed to play video
        </h3>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          The video file may be corrupted or in an unsupported format
        </p>
      </div>
    );
  }

  return (
    <div className="w-full rounded-2xl overflow-hidden">
      <VideoRenderer
        url={videoUrl}
        loop={true}
      />
    </div>
  );
}

interface ImageEditGenerateToolViewProps extends ToolViewProps {
  onFileClick?: (filePath: string) => void;
}

export function ImageEditGenerateToolView({
  toolCall,
  toolResult,
  isStreaming = false,
  project,
}: ImageEditGenerateToolViewProps) {
  const {
    prompt,
    status,
    generatedImagePaths,
    generatedVideoPaths,
    isVideoMode,
    error,
    batchResults,
  } = useMemo(() => {
    if (!toolCall) {
      return {
        prompt: null as string | null,
        status: null as string | null,
        generatedImagePaths: [] as string[],
        generatedVideoPaths: [] as string[],
        isVideoMode: false,
        error: null as string | null,
        batchResults: [] as Array<{ success: boolean; error?: string }>,
      };
    }
    return extractImageEditGenerateData(toolCall, toolResult, true);
  }, [toolCall, toolResult]);

  const sandboxId = project?.sandbox?.id;
  const imagePath = generatedImagePaths[0];
  const videoPath = generatedVideoPaths[0];
  const hasMedia = imagePath || videoPath;

  // ONLY show error if:
  // 1. Not streaming (still processing)
  // 2. We have a result (toolResult exists)
  // 3. The result explicitly failed (has error or failed batch)
  // 4. No media was produced
  const hasActualError = !isStreaming &&
    toolResult &&
    !hasMedia &&
    (!!error || (batchResults.length > 0 && !batchResults[0].success));

  const actualIsSuccess = hasMedia && !hasActualError;
  const isLoadingState = (isStreaming || !toolResult || (!hasMedia && !hasActualError)) && !actualIsSuccess;
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [loadingElapsedMs, setLoadingElapsedMs] = useState(0);

  React.useEffect(() => {
    if (!isLoadingState) {
      setLoadingElapsedMs(0);
      return;
    }

    const startedAt = Date.now();
    setLoadingElapsedMs(0);

    const timer = setInterval(() => {
      setLoadingElapsedMs(Date.now() - startedAt);
    }, 300);

    return () => clearInterval(timer);
  }, [isLoadingState, toolCall?.tool_call_id]);

  const loadingProgress = useMemo(() => {
    if (!isLoadingState) {
      return 100;
    }

    if (loadingElapsedMs < 1500) {
      return 12 + (loadingElapsedMs / 1500) * 14;
    }
    if (loadingElapsedMs < 5000) {
      return 26 + ((loadingElapsedMs - 1500) / 3500) * 28;
    }
    if (loadingElapsedMs < 9000) {
      return 54 + ((loadingElapsedMs - 5000) / 4000) * 20;
    }
    return Math.min(92, 74 + ((loadingElapsedMs - 9000) / 6000) * 18);
  }, [isLoadingState, loadingElapsedMs]);

  const loadingStatusLabel = useMemo(() => {
    if (status && typeof status === 'string' && status.trim()) {
      return status.trim();
    }

    if (loadingElapsedMs < 1500) {
      return 'Preparing media request';
    }
    if (loadingElapsedMs < 5000) {
      return isVideoMode ? 'Generating video frames' : 'Generating image';
    }
    if (loadingElapsedMs < 9000) {
      return isVideoMode ? 'Rendering final video' : 'Refining details';
    }
    return 'Finalizing output';
  }, [status, loadingElapsedMs, isVideoMode]);

  // Get media blob URL for download
  const { data: mediaBlob } = useFileContentQuery(sandboxId, videoPath || imagePath, {
    contentType: 'blob',
    enabled: !!sandboxId && !!(videoPath || imagePath) && actualIsSuccess && !!toolCall,
  });

  // Create and manage download URL
  React.useEffect(() => {
    if (mediaBlob instanceof Blob) {
      const newUrl = URL.createObjectURL(mediaBlob);
      setDownloadUrl(newUrl);

      return () => {
        URL.revokeObjectURL(newUrl);
        setDownloadUrl(null);
      };
    } else {
      setDownloadUrl(null);
    }
  }, [mediaBlob]);

  if (!toolCall) return null;

  const handleDownload = () => {
    if (!downloadUrl) return;
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = (videoPath || imagePath || 'media').split('/').pop() || 'media';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <Card className="gap-0 flex border-0 shadow-none p-0 py-0 rounded-none flex-col h-full overflow-hidden bg-card">
      {/* Header */}
      <CardHeader className="h-14 bg-zinc-50/80 dark:bg-zinc-900/80 backdrop-blur-sm border-b p-2 px-4 space-y-2">
        <div className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative p-2 rounded-lg border shrink-0 bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700">
              {videoPath ? (
                <VideoIcon className="w-5 h-5 text-zinc-600 dark:text-zinc-400" />
              ) : (
                <ImageIcon className="w-5 h-5 text-zinc-600 dark:text-zinc-400" />
              )}
            </div>
            <div>
              <CardTitle className="text-base font-medium text-zinc-900 dark:text-zinc-100">
                Generate Media
              </CardTitle>
            </div>
          </div>

          {/* Download button */}
          {actualIsSuccess && downloadUrl && (
            <Button
              onClick={handleDownload}
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 px-2"
            >
              <Download className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Download</span>
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {isStreaming || !toolResult ? (
          <MediaLoadingState
            aspectVideo={isVideoMode}
            progress={loadingProgress}
            statusLabel={loadingStatusLabel}
            prompt={prompt}
          />
        ) : hasActualError ? (
          /* Error State - Only after streaming complete AND actual failure */
          <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4 bg-gradient-to-b from-zinc-100 to-zinc-50 dark:from-zinc-800/40 dark:to-zinc-900/60">
              <AlertTriangle className="h-8 w-8 text-zinc-500 dark:text-zinc-400" />
            </div>
            <h3 className="text-base font-medium text-zinc-900 dark:text-zinc-100 mb-2">
              Processing Failed
            </h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 max-w-md">
              {error || batchResults[0]?.error || 'An error occurred during processing.'}
            </p>
          </div>
        ) : videoPath ? (
          /* Success State - Show FULL video player */
          <VideoRendererFull filePath={videoPath} sandboxId={sandboxId} />
        ) : imagePath ? (
          /* Success State - Show image */
          <ImageDisplay filePath={imagePath} sandboxId={sandboxId} />
        ) : (
          <MediaLoadingState
            aspectVideo={isVideoMode}
            progress={loadingProgress}
            statusLabel={loadingStatusLabel}
            prompt={prompt}
          />
        )}
      </CardContent>
    </Card>
  );
}
