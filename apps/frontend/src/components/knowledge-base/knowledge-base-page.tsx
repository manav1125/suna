'use client';

import React from 'react';
import { KnowledgeBasePageHeader } from './knowledge-base-header';
import { KnowledgeBaseManager } from './knowledge-base-manager';

export function KnowledgeBasePage() {
    return (
        <div className="container mx-auto max-w-7xl px-3 sm:px-4 py-4 sm:py-8">
            <div className="space-y-4 sm:space-y-8">
                <KnowledgeBasePageHeader />
                <div className="w-full">
                    <KnowledgeBaseManager
                        showHeader={true}
                        headerTitle="Library"
                        headerDescription="Upload documents once, organize them into folders, then assign the right files to each worker from its Knowledge tab."
                        showRecentFiles={false}
                        enableAssignments={false}
                        emptyStateMessage="Start by adding files to your shared knowledge library. You can assign them to individual workers from each worker's Knowledge tab."
                    />
                </div>
            </div>
        </div>
    );
}
