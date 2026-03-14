'use client';

import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AudioLines, Loader2, MicOff, PhoneOff, PhoneOutgoing } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { backendApi } from '@/lib/api-client';
import { threadKeys } from '@/hooks/threads/keys';

type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error';

interface TranscriptPreview {
  role: 'user' | 'assistant';
  text: string;
}

interface PersistableTranscriptTurn {
  role: 'user' | 'assistant';
  text: string;
  timestamp?: number | null;
  dedupeSuffix?: string;
}

interface VapiSessionResponse {
  public_key: string;
  assistant: Record<string, unknown>;
  thread_id: string;
  agent_id?: string | null;
  agent_name?: string | null;
}

interface VapiHandoffResponse {
  status: string;
  message?: {
    message_id?: string;
  };
  message_id?: string;
}

interface LiveVoiceButtonProps {
  threadId: string;
  selectedAgentId?: string;
  disabled?: boolean;
}

export const LiveVoiceButton: React.FC<LiveVoiceButtonProps> = memo(function LiveVoiceButton({
  threadId,
  selectedAgentId,
  disabled = false,
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('Ready to start a live conversation.');
  const [isMuted, setIsMuted] = useState(false);
  const [transcriptPreview, setTranscriptPreview] = useState<TranscriptPreview[]>([]);
  const [activeAgentName, setActiveAgentName] = useState<string>('Mira');

  const vapiRef = useRef<any>(null);
  const transcriptTurnsRef = useRef<PersistableTranscriptTurn[]>([]);
  const transcriptKeysRef = useRef<Set<string>>(new Set());
  const handoffPersistedRef = useRef(false);
  const callIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (vapiRef.current) {
        try {
          vapiRef.current.stop();
        } catch (error) {
          console.warn('Failed to stop Vapi session on unmount', error);
        }
      }
    };
  }, []);

  const normalizeRole = useCallback((value: unknown): 'user' | 'assistant' | null => {
    const normalized = String(value || '').toLowerCase();
    if (!normalized) return null;
    if (normalized === 'user') return 'user';
    if (['assistant', 'bot', 'agent', 'model', 'system'].includes(normalized)) return 'assistant';
    return null;
  }, []);

  const extractText = useCallback((value: unknown): string => {
    if (!value) return '';
    if (typeof value === 'string') return value.trim();
    if (Array.isArray(value)) {
      return value
        .map((item) => extractText(item))
        .filter(Boolean)
        .join(' ')
        .trim();
    }
    if (typeof value === 'object') {
      const record = value as Record<string, unknown>;
      return (
        extractText(record.transcript) ||
        extractText(record.text) ||
        extractText(record.message) ||
        extractText(record.content) ||
        ''
      ).trim();
    }
    return String(value).trim();
  }, []);

  const extractTranscriptTurns = useCallback((message: any): PersistableTranscriptTurn[] => {
    const turns: PersistableTranscriptTurn[] = [];
    const seen = new Set<string>();
    const type = String(message?.type || '').toLowerCase();

    const pushTurn = (
      roleValue: unknown,
      textValue: unknown,
      timestamp?: number | null,
      dedupeSuffix?: string
    ) => {
      const role = normalizeRole(roleValue);
      const text = extractText(textValue);
      if (!role || !text) return;

      const localKey = `${role}::${timestamp ?? ''}::${dedupeSuffix ?? ''}::${text}`;
      if (seen.has(localKey)) return;
      seen.add(localKey);

      turns.push({ role, text, timestamp: timestamp ?? null, dedupeSuffix });
    };

    const directTranscriptType = String(
      message?.transcriptType ||
      message?.transcript?.type ||
      message?.message?.transcriptType ||
      ''
    ).toLowerCase();
    const isDirectTranscriptEvent =
      type.includes('transcript') ||
      Boolean(message?.transcript) ||
      Boolean(message?.message?.transcript);
    const looksFinalDirectTurn =
      !directTranscriptType || directTranscriptType === 'final' || type.includes('final');

    if (isDirectTranscriptEvent && looksFinalDirectTurn) {
      pushTurn(
        message?.role ?? message?.speaker ?? message?.from,
        message?.transcript ?? message?.message?.transcript ?? message?.content ?? message?.message,
        message?.timestamp ?? null,
        'direct'
      );
    }

    const collections = [
      message?.conversation,
      message?.messages,
      message?.artifact?.messages,
      message?.message?.conversation,
      message?.message?.messages,
      message?.message?.artifact?.messages,
    ].filter(Array.isArray) as Array<any[]>;

    collections.forEach((collection, collectionIndex) => {
      collection.forEach((item, itemIndex) => {
        const itemTranscriptType = String(
          item?.transcriptType || item?.transcript?.type || ''
        ).toLowerCase();
        const shouldSkipInterim = itemTranscriptType && itemTranscriptType !== 'final';
        if (shouldSkipInterim) return;

        pushTurn(
          item?.role ?? item?.speaker ?? item?.from,
          item?.transcript ?? item?.message ?? item?.content ?? item?.text,
          item?.timestamp ?? item?.time ?? message?.timestamp ?? null,
          `collection-${collectionIndex}-${itemIndex}`
        );
      });
    });

    return turns;
  }, [extractText, normalizeRole]);

  const buildTurnKey = useCallback((turn: PersistableTranscriptTurn) => {
    return [turn.role, turn.timestamp ?? '', turn.text.trim()].join('::');
  }, []);

  const mergeTranscriptTurns = useCallback((turns: PersistableTranscriptTurn[]) => {
    let changed = false;

    for (const turn of turns) {
      const text = turn.text.trim();
      if (!text) continue;

      const normalizedTurn = {
        role: turn.role,
        text,
        timestamp: turn.timestamp ?? null,
      };

      const key = buildTurnKey(normalizedTurn);
      if (transcriptKeysRef.current.has(key)) {
        continue;
      }

      transcriptKeysRef.current.add(key);
      transcriptTurnsRef.current.push(normalizedTurn);
      changed = true;
    }

    if (changed) {
      setTranscriptPreview(transcriptTurnsRef.current.slice(-8));
    }
  }, [buildTurnKey]);

  const persistCallHandoff = useCallback(async () => {
    if (handoffPersistedRef.current) {
      return true;
    }

    const turns = transcriptTurnsRef.current
      .map((turn) => ({
        role: turn.role,
        text: turn.text.trim(),
        timestamp: turn.timestamp ?? null,
      }))
      .filter((turn) => turn.text);

    if (turns.length === 0) {
      return false;
    }

    handoffPersistedRef.current = true;
    setStatusText('Saving call handoff to chat...');

    const response = await backendApi.post<VapiHandoffResponse>(
      `/vapi/web/handoff/${threadId}`,
      {
        turns,
        call_id: callIdRef.current,
        agent_id: selectedAgentId ?? null,
        agent_name: activeAgentName,
      },
      {
        showErrors: false,
        timeout: 30000,
      }
    );

    if (response.error) {
      handoffPersistedRef.current = false;
      console.error('Failed to persist live voice handoff', response.error);
      setErrorMessage(response.error.message || 'Could not save the call handoff to chat.');
      setStatusText('Voice ended, but the handoff could not be saved.');
      return false;
    }

    void queryClient.invalidateQueries({ queryKey: threadKeys.messages(threadId) });
    setStatusText('Call handoff saved to chat.');
    return true;
  }, [activeAgentName, queryClient, selectedAgentId, threadId]);

  const stopSession = useCallback(async () => {
    if (!vapiRef.current) {
      setConnectionState('idle');
      setIsMuted(false);
      return;
    }

    try {
      await vapiRef.current.stop();
    } catch (error) {
      console.warn('Failed to stop Vapi session cleanly', error);
    } finally {
      vapiRef.current = null;
      if (mountedRef.current) {
        setConnectionState('idle');
        setIsMuted(false);
      }
    }
  }, []);

  const handleVapiMessage = useCallback((message: any) => {
    const type = String(message?.type || '');

    if (type === 'status-update' && message?.status) {
      setStatusText(`Status: ${message.status}`);
    }

    if (message?.call?.id) {
      callIdRef.current = message.call.id;
    }

    const turns = extractTranscriptTurns(message);
    if (turns.length === 0) {
      return;
    }

    mergeTranscriptTurns(turns);
  }, [extractTranscriptTurns, mergeTranscriptTurns]);

  const startSession = useCallback(async () => {
    setConnectionState('connecting');
    setErrorMessage(null);
    setStatusText('Preparing live voice...');
    setTranscriptPreview([]);
    transcriptTurnsRef.current = [];
    transcriptKeysRef.current.clear();
    handoffPersistedRef.current = false;
    callIdRef.current = null;

    const sessionResponse = await backendApi.post<VapiSessionResponse>(
      `/vapi/web/session/${threadId}`,
      {
        agent_id: selectedAgentId ?? null,
      },
      {
        showErrors: false,
        timeout: 20000,
      }
    );

    if (sessionResponse.error || !sessionResponse.data) {
      const detail = sessionResponse.error?.message || 'Unable to start live voice right now.';
      setConnectionState('error');
      setErrorMessage(detail);
      setStatusText('Live voice could not start.');
      return;
    }

    setActiveAgentName(sessionResponse.data.agent_name || 'Mira');

    try {
      const { default: Vapi } = await import('@vapi-ai/web');
      const vapi = new Vapi(sessionResponse.data.public_key);
      vapiRef.current = vapi;

      vapi.on('call-start', () => {
        if (!mountedRef.current) return;
        setConnectionState('connected');
        setStatusText(`Live with ${sessionResponse.data?.agent_name || 'Mira'}.`);
      });

      vapi.on('call-end', () => {
        void (async () => {
          await persistCallHandoff();
          if (!mountedRef.current) return;
          vapiRef.current = null;
          setConnectionState('idle');
          setIsMuted(false);
        })();
      });

      vapi.on('speech-start', () => {
        if (!mountedRef.current) return;
        setStatusText(`${sessionResponse.data?.agent_name || 'Mira'} is speaking...`);
      });

      vapi.on('speech-end', () => {
        if (!mountedRef.current) return;
        setStatusText(isMuted ? 'Muted' : 'Listening...');
      });

      vapi.on('message', (message: any) => {
        void handleVapiMessage(message);
      });

      vapi.on('call-start-failed', (event: any) => {
        console.error('Vapi live voice call-start-failed', event);
        if (!mountedRef.current) return;
        const detail =
          event?.error ||
          event?.context?.error ||
          event?.context?.message ||
          'Live voice failed to connect.';
        setConnectionState('error');
        setErrorMessage(String(detail));
        setStatusText('Live voice could not connect.');
      });

      vapi.on('error', (error: any) => {
        console.error('Vapi live voice error', error);
        if (!mountedRef.current) return;
        const detail =
          error?.message ||
          error?.error?.message ||
          error?.errorMsg ||
          error?.error ||
          'Live voice hit an unexpected error.';
        setConnectionState('error');
        setErrorMessage(String(detail));
        setStatusText('Live voice encountered an error.');
      });

      await vapi.start(sessionResponse.data.assistant);
    } catch (error: any) {
      console.error('Failed to initialize Vapi live voice', error);
      setConnectionState('error');
      setErrorMessage(error?.message || 'Live voice could not initialize.');
      setStatusText('Live voice could not initialize.');
    }
  }, [handleVapiMessage, isMuted, persistCallHandoff, selectedAgentId, threadId]);

  const handleToggleMute = useCallback(() => {
    if (!vapiRef.current || connectionState !== 'connected') {
      return;
    }

    const nextMuted = !isMuted;
    vapiRef.current.setMuted(nextMuted);
    setIsMuted(nextMuted);
    setStatusText(nextMuted ? 'Muted' : 'Listening...');
  }, [connectionState, isMuted]);

  const buttonLabel = useMemo(() => {
    if (connectionState === 'connecting') return 'Connecting voice';
    if (connectionState === 'connected') return 'End live voice';
    return 'Start live voice';
  }, [connectionState]);

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={disabled}
            onClick={() => setOpen(true)}
            className="h-10 px-2 py-2 bg-transparent border-[1.5px] border-border rounded-2xl text-muted-foreground hover:text-foreground hover:bg-accent/50 flex items-center gap-2 transition-colors"
          >
            <AudioLines className="h-5 w-5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          <p>Live voice with Mira</p>
        </TooltipContent>
      </Tooltip>

      <Dialog
        open={open}
        onOpenChange={(nextOpen) => {
          setOpen(nextOpen);
          if (!nextOpen && (connectionState === 'connected' || connectionState === 'connecting')) {
            void stopSession();
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Live voice with {activeAgentName}</DialogTitle>
            <DialogDescription>
              Talk through ideas in this thread in real time. When the call ends, Mira saves a structured handoff and the full transcript back into chat so the thread can continue cleanly. For heavy research or long-running work, follow up in chat after the call.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-2xl border border-border/60 bg-muted/30 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Status</p>
                  <p className="text-sm text-muted-foreground">{statusText}</p>
                </div>
                {connectionState === 'connecting' ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  <div
                    className={`h-3 w-3 rounded-full ${
                      connectionState === 'connected'
                        ? 'bg-emerald-500'
                        : connectionState === 'error'
                          ? 'bg-destructive'
                          : 'bg-muted-foreground/40'
                    }`}
                  />
                )}
              </div>
            </div>

            {errorMessage && (
              <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                {errorMessage}
              </div>
            )}

            <div className="flex flex-wrap items-center gap-2">
              {connectionState === 'connected' ? (
                <>
                  <Button type="button" onClick={() => void stopSession()} className="gap-2">
                    <PhoneOff className="h-4 w-4" />
                    End voice
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleToggleMute}
                    className="gap-2"
                  >
                    <MicOff className="h-4 w-4" />
                    {isMuted ? 'Unmute' : 'Mute'}
                  </Button>
                </>
              ) : (
                <Button
                  type="button"
                  onClick={() => void startSession()}
                  disabled={connectionState === 'connecting'}
                  className="gap-2"
                >
                  <PhoneOutgoing className="h-4 w-4" />
                  {buttonLabel}
                </Button>
              )}
            </div>

            <div className="rounded-2xl border border-border/60 bg-background p-4">
              <p className="mb-2 text-sm font-medium">Recent transcript</p>
              {transcriptPreview.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Once you start talking, the latest user and assistant turns will show up here.
                </p>
              ) : (
                <div className="space-y-2">
                  {transcriptPreview.map((turn, index) => (
                    <div key={`${turn.role}-${index}`} className="text-sm">
                      <span className="font-medium capitalize">{turn.role}:</span>{' '}
                      <span className="text-muted-foreground">{turn.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});
