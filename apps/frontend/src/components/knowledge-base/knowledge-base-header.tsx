'use client';

import React from 'react';
import { BookOpen } from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';

export const KnowledgeBasePageHeader = () => {
  return (
    <PageHeader icon={BookOpen}>
      <div className="space-y-2 sm:space-y-4">
        <div className="text-4xl font-semibold tracking-tight">
          <span className="text-primary">Knowledge Base</span>
        </div>
        <p className="mx-auto max-w-2xl text-sm sm:text-base text-muted-foreground">
          Keep a shared document library for your workspace, then assign the relevant files to each worker as needed.
        </p>
      </div>
    </PageHeader>
  );
};
