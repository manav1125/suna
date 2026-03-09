'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
    FileIcon,
    FolderIcon,
    Loader2Icon,
    SearchIcon,
    Users2Icon,
} from 'lucide-react';
import { useAgents } from '@/hooks/agents/use-agents';
import type { Agent } from '@/hooks/agents/utils';
import { createClient } from '@/lib/supabase/client';
import { cn } from '@/lib/utils';
import { toast } from '@/lib/toast';
import { AgentAvatar } from '@/components/thread/content/agent-avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

type AssignmentState = 'assigned' | 'partial' | 'unassigned';

export interface WorkerAssignmentTarget {
    id: string;
    name: string;
    type: 'folder' | 'file';
    entryIds: string[];
    fileCount: number;
}

interface WorkerAssignmentModalProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    target: WorkerAssignmentTarget | null;
}

const getAssignmentState = (targetEntryIds: string[], assignedEntryIds: string[]): AssignmentState => {
    const assignedSet = new Set(assignedEntryIds);
    const selectedCount = targetEntryIds.filter((entryId) => assignedSet.has(entryId)).length;

    if (selectedCount === 0) {
        return 'unassigned';
    }

    if (selectedCount === targetEntryIds.length) {
        return 'assigned';
    }

    return 'partial';
};

const getStateMeta = (state: AssignmentState) => {
    switch (state) {
        case 'assigned':
            return {
                label: 'Assigned',
                className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
            };
        case 'partial':
            return {
                label: 'Partial',
                className: 'border-amber-200 bg-amber-50 text-amber-700',
            };
        default:
            return {
                label: 'Not assigned',
                className: 'border-border bg-muted/40 text-muted-foreground',
            };
    }
};

export function KBWorkerAssignmentModal({
    isOpen,
    onOpenChange,
    target,
}: WorkerAssignmentModalProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [loadingAssignments, setLoadingAssignments] = useState(false);
    const [saving, setSaving] = useState(false);
    const [assignmentSets, setAssignmentSets] = useState<Record<string, string[]>>({});
    const [currentStates, setCurrentStates] = useState<Record<string, AssignmentState>>({});
    const [draftStates, setDraftStates] = useState<Record<string, AssignmentState>>({});

    const { data: agentsResponse, isLoading: agentsLoading } = useAgents(
        { limit: 100 },
        { enabled: isOpen }
    );

    const agents = useMemo(
        () => (Array.isArray(agentsResponse?.agents) ? agentsResponse.agents : []),
        [agentsResponse?.agents]
    );

    const targetEntryKey = useMemo(
        () => (target ? [...target.entryIds].sort().join('|') : ''),
        [target]
    );

    useEffect(() => {
        if (!isOpen) {
            setSearchQuery('');
            setAssignmentSets({});
            setCurrentStates({});
            setDraftStates({});
        }
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen || !target || agents.length === 0) {
            return;
        }

        let cancelled = false;

        const loadAssignments = async () => {
            setLoadingAssignments(true);

            try {
                const supabase = createClient();
                const { data: { session } } = await supabase.auth.getSession();

                if (!session?.access_token) {
                    throw new Error('No session available');
                }

                const results = await Promise.all(
                    agents.map(async (agent) => {
                        const response = await fetch(`${API_URL}/knowledge-base/agents/${agent.agent_id}/assignments`, {
                            headers: {
                                'Authorization': `Bearer ${session.access_token}`,
                                'Content-Type': 'application/json',
                            },
                        });

                        if (!response.ok) {
                            throw new Error(`Failed to load assignments for ${agent.name}`);
                        }

                        const assignments = await response.json();
                        const enabledEntryIds = Object.entries(assignments)
                            .filter(([, enabled]) => Boolean(enabled))
                            .map(([entryId]) => entryId);

                        return [agent.agent_id, enabledEntryIds] as const;
                    })
                );

                if (cancelled) {
                    return;
                }

                const nextAssignmentSets = Object.fromEntries(results);
                const nextStates = Object.fromEntries(
                    results.map(([agentId, enabledEntryIds]) => [
                        agentId,
                        getAssignmentState(target.entryIds, enabledEntryIds),
                    ])
                );

                setAssignmentSets(nextAssignmentSets);
                setCurrentStates(nextStates);
                setDraftStates(nextStates);
            } catch (error) {
                console.error('Failed to load worker knowledge assignments:', error);
                if (!cancelled) {
                    toast.warning('Failed to load worker assignments');
                }
            } finally {
                if (!cancelled) {
                    setLoadingAssignments(false);
                }
            }
        };

        void loadAssignments();

        return () => {
            cancelled = true;
        };
    }, [agents, isOpen, target, targetEntryKey]);

    const filteredAgents = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        const filtered = query
            ? agents.filter((agent) => agent.name.toLowerCase().includes(query))
            : agents;

        const stateRank = (state: AssignmentState) => {
            switch (state) {
                case 'assigned':
                    return 0;
                case 'partial':
                    return 1;
                default:
                    return 2;
            }
        };

        return [...filtered].sort((left, right) => {
            const stateDiff = stateRank(draftStates[left.agent_id] || 'unassigned') - stateRank(draftStates[right.agent_id] || 'unassigned');
            if (stateDiff !== 0) {
                return stateDiff;
            }

            return left.name.localeCompare(right.name);
        });
    }, [agents, draftStates, searchQuery]);

    const selectedWorkersCount = useMemo(
        () => agents.filter((agent) => draftStates[agent.agent_id] === 'assigned').length,
        [agents, draftStates]
    );

    const pendingChangesCount = useMemo(
        () => agents.filter((agent) => draftStates[agent.agent_id] !== currentStates[agent.agent_id]).length,
        [agents, currentStates, draftStates]
    );

    const toggleAgent = (agentId: string) => {
        setDraftStates((previous) => {
            const currentState = previous[agentId] || 'unassigned';

            return {
                ...previous,
                [agentId]: currentState === 'assigned' ? 'unassigned' : 'assigned',
            };
        });
    };

    const getTargetStatusCopy = (agentId: string) => {
        if (!target) {
            return '';
        }

        const totalFiles = target.entryIds.length;
        const assignedCount = target.entryIds.filter((entryId) => (assignmentSets[agentId] || []).includes(entryId)).length;
        const currentState = currentStates[agentId] || 'unassigned';
        const draftState = draftStates[agentId] || 'unassigned';

        if (draftState !== currentState) {
            if (draftState === 'assigned') {
                return totalFiles === 1
                    ? 'Will gain access on save'
                    : `Will gain access to all ${totalFiles} files`;
            }

            return totalFiles === 1
                ? 'Will lose access on save'
                : `Will lose access to all ${totalFiles} files`;
        }

        if (currentState === 'assigned') {
            return totalFiles === 1
                ? 'Already has access'
                : `Already has all ${totalFiles} files`;
        }

        if (currentState === 'partial') {
            return `Currently has ${assignedCount} of ${totalFiles} files`;
        }

        return totalFiles === 1
            ? 'No access yet'
            : `No access to these ${totalFiles} files`;
    };

    const applyAssignmentUpdate = async (
        agent: Agent,
        accessToken: string
    ) => {
        if (!target) {
            return null;
        }

        const currentState = currentStates[agent.agent_id] || 'unassigned';
        const nextState = draftStates[agent.agent_id] || 'unassigned';

        if (currentState === nextState) {
            return null;
        }

        const nextAssignments = new Set(assignmentSets[agent.agent_id] || []);

        if (nextState === 'assigned') {
            target.entryIds.forEach((entryId) => nextAssignments.add(entryId));
        } else {
            target.entryIds.forEach((entryId) => nextAssignments.delete(entryId));
        }

        const response = await fetch(`${API_URL}/knowledge-base/agents/${agent.agent_id}/assignments`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ entry_ids: Array.from(nextAssignments) }),
        });

        if (!response.ok) {
            throw new Error(`Failed to update assignments for ${agent.name}`);
        }

        return {
            agentId: agent.agent_id,
            entryIds: Array.from(nextAssignments),
            nextState,
        };
    };

    const handleSave = async () => {
        if (!target || saving) {
            return;
        }

        if (pendingChangesCount === 0) {
            onOpenChange(false);
            return;
        }

        setSaving(true);

        try {
            const supabase = createClient();
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error('No session available');
            }

            const results = await Promise.allSettled(
                agents.map((agent) => applyAssignmentUpdate(agent, session.access_token))
            );

            const successfulUpdates = results
                .filter((result): result is PromiseFulfilledResult<Awaited<ReturnType<typeof applyAssignmentUpdate>>> => result.status === 'fulfilled')
                .map((result) => result.value)
                .filter((value): value is NonNullable<typeof value> => Boolean(value));

            if (successfulUpdates.length > 0) {
                setAssignmentSets((previous) => {
                    const next = { ...previous };
                    successfulUpdates.forEach((update) => {
                        next[update.agentId] = update.entryIds;
                    });
                    return next;
                });

                setCurrentStates((previous) => {
                    const next = { ...previous };
                    successfulUpdates.forEach((update) => {
                        next[update.agentId] = update.nextState;
                    });
                    return next;
                });

                setDraftStates((previous) => {
                    const next = { ...previous };
                    successfulUpdates.forEach((update) => {
                        next[update.agentId] = update.nextState;
                    });
                    return next;
                });
            }

            const failedUpdates = results.filter((result) => result.status === 'rejected');

            if (failedUpdates.length === 0) {
                toast.message(
                    `Updated worker access for ${successfulUpdates.length} worker${successfulUpdates.length === 1 ? '' : 's'}`
                );
                onOpenChange(false);
                return;
            }

            if (successfulUpdates.length > 0) {
                toast.warning(
                    `Updated ${successfulUpdates.length} worker${successfulUpdates.length === 1 ? '' : 's'}, but ${failedUpdates.length} failed`
                );
                return;
            }

            toast.warning('Failed to update worker assignments');
        } catch (error) {
            console.error('Failed to save worker knowledge assignments:', error);
            toast.warning('Failed to update worker assignments');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog
            open={isOpen}
            onOpenChange={(open) => {
                if (!saving) {
                    onOpenChange(open);
                }
            }}
        >
            <DialogContent className="max-w-2xl gap-0 p-0 overflow-hidden">
                <DialogHeader className="px-6 pt-6 pb-4">
                    <div className="flex items-start gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border bg-muted/50">
                            {target?.type === 'folder' ? (
                                <FolderIcon className="h-5 w-5 text-foreground" />
                            ) : (
                                <FileIcon className="h-5 w-5 text-foreground" />
                            )}
                        </div>
                        <div className="min-w-0 space-y-1">
                            <DialogTitle className="flex items-center gap-2">
                                <span className="truncate">Assign to Workers</span>
                            </DialogTitle>
                            <DialogDescription className="pr-8">
                                {target ? (
                                    <>
                                        Choose which workers should be able to use{' '}
                                        <span className="font-medium text-foreground">{target.name}</span>.
                                        {target.fileCount > 1 ? ` This will update all ${target.fileCount} files in that folder.` : ''}
                                    </>
                                ) : (
                                    'Choose which workers should be able to use this knowledge item.'
                                )}
                            </DialogDescription>
                        </div>
                    </div>

                    {target && (
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                            <Badge variant="outline" className="rounded-full">
                                <Users2Icon className="mr-1 h-3 w-3" />
                                {selectedWorkersCount} worker{selectedWorkersCount === 1 ? '' : 's'} selected
                            </Badge>
                            <Badge variant="outline" className="rounded-full">
                                {target.fileCount} file{target.fileCount === 1 ? '' : 's'}
                            </Badge>
                            {pendingChangesCount > 0 && (
                                <Badge className="rounded-full bg-primary/10 text-primary hover:bg-primary/10">
                                    {pendingChangesCount} pending change{pendingChangesCount === 1 ? '' : 's'}
                                </Badge>
                            )}
                        </div>
                    )}
                </DialogHeader>

                <Separator />

                <div className="px-6 py-4">
                    <div className="relative">
                        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            placeholder="Search workers..."
                            className="pl-9"
                        />
                    </div>
                </div>

                <ScrollArea className="max-h-[420px] px-6 pb-2">
                    <div className="space-y-3 pb-4">
                        {(agentsLoading || loadingAssignments) && (
                            <>
                                {[1, 2, 3, 4].map((row) => (
                                    <div key={row} className="rounded-2xl border p-4">
                                        <div className="flex items-center gap-3">
                                            <Skeleton className="h-5 w-5 rounded-sm" />
                                            <Skeleton className="h-10 w-10 rounded-full" />
                                            <div className="flex-1 space-y-2">
                                                <Skeleton className="h-4 w-32" />
                                                <Skeleton className="h-3 w-40" />
                                            </div>
                                            <Skeleton className="h-6 w-20 rounded-full" />
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}

                        {!agentsLoading && !loadingAssignments && filteredAgents.length === 0 && (
                            <div className="rounded-2xl border border-dashed px-6 py-12 text-center">
                                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border bg-muted/40">
                                    <Users2Icon className="h-5 w-5 text-muted-foreground" />
                                </div>
                                <h4 className="text-sm font-semibold">No workers found</h4>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    {agents.length === 0
                                        ? 'Create a worker first to start assigning knowledge.'
                                        : 'Try a different search term.'}
                                </p>
                            </div>
                        )}

                        {!agentsLoading && !loadingAssignments && filteredAgents.map((agent) => {
                            const draftState = draftStates[agent.agent_id] || 'unassigned';
                            const meta = getStateMeta(draftState);
                            const currentState = currentStates[agent.agent_id] || 'unassigned';

                            return (
                                <button
                                    key={agent.agent_id}
                                    type="button"
                                    onClick={() => toggleAgent(agent.agent_id)}
                                    className={cn(
                                        'flex w-full items-center gap-4 rounded-2xl border p-4 text-left transition-colors',
                                        draftState === 'assigned' && 'border-primary/40 bg-primary/5',
                                        draftState === 'partial' && 'border-amber-200 bg-amber-50/40',
                                        draftState === 'unassigned' && 'border-border hover:bg-muted/30'
                                    )}
                                >
                                    <Checkbox
                                        checked={draftState === 'partial' ? 'indeterminate' : draftState === 'assigned'}
                                        onCheckedChange={() => toggleAgent(agent.agent_id)}
                                        onClick={(event) => event.stopPropagation()}
                                    />
                                    <AgentAvatar
                                        agentId={agent.agent_id}
                                        size={40}
                                        fallbackName={agent.name}
                                        className="shrink-0"
                                    />
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="truncate font-medium">{agent.name}</span>
                                            <Badge variant="outline" className={cn('rounded-full', meta.className)}>
                                                {meta.label}
                                            </Badge>
                                            {draftState !== currentState && (
                                                <Badge variant="outline" className="rounded-full border-primary/30 bg-primary/5 text-primary">
                                                    Pending
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="mt-1 text-sm text-muted-foreground">
                                            {getTargetStatusCopy(agent.agent_id)}
                                        </p>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </ScrollArea>

                <Separator />

                <DialogFooter className="px-6 py-4">
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={saving}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={!target || saving || agentsLoading || loadingAssignments}
                        className="gap-2"
                    >
                        {saving && <Loader2Icon className="h-4 w-4 animate-spin" />}
                        Save Assignments
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
