'use client';

import { useTranslations } from 'next-intl';
import { KnowledgeBaseManager } from '@/components/knowledge-base/knowledge-base-manager';

export function KnowledgeBaseSettings() {
  const t = useTranslations('settings.knowledgeBase');

  return (
    <div className="p-4 sm:p-6 pb-12 sm:pb-6 space-y-5 sm:space-y-6 min-w-0 max-w-full overflow-x-hidden">
      <KnowledgeBaseManager
        showHeader={true}
        headerTitle={t('title') || 'Knowledge Base'}
        headerDescription={t('description') || 'Upload and manage documents for your agents'}
        showRecentFiles={false}
        enableAssignments={false}
        emptyStateMessage="Upload documents here once, then assign the right files to each worker from that worker's Knowledge tab."
      />
    </div>
  );
}
