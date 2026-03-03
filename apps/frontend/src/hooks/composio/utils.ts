import { backendApi } from '@/lib/api-client';

const COMPOSIO_REQUEST_TIMEOUT_MS = 12000;

export interface ComposioCategory {
  id: string;
  name: string;
}

export interface CompositoCategoriesResponse {
  success: boolean;
  categories: ComposioCategory[];
  total: number;
  error?: string;
}

export interface ComposioToolkit {
  slug: string;
  name: string;
  description?: string;
  logo?: string;
  tags: string[];
  auth_schemes: string[];
  categories: string[];
}

export interface AuthConfigField {
  name: string;
  displayName: string;
  type: string;
  description?: string;
  required: boolean;
  default?: string;
  legacy_template_name?: string;
}

export interface AuthConfigDetails {
  name: string;
  mode: string;
  fields: {
    [fieldType: string]: {
      [requirementLevel: string]: AuthConfigField[];
    };
  };
}

export interface DetailedComposioToolkit {
  slug: string;
  name: string;
  description?: string;
  logo?: string;
  tags: string[];
  auth_schemes: string[];
  categories: string[];
  auth_config_details: AuthConfigDetails[];
  connected_account_initiation_fields?: {
    [requirementLevel: string]: AuthConfigField[];
  };
  base_url?: string;
}

export interface DetailedComposioToolkitResponse {
  success: boolean;
  toolkit: DetailedComposioToolkit;
  error?: string;
}

export interface ComposioTool {
  slug: string;
  name: string;
  description: string;
  version: string;
  input_parameters: {
    properties: Record<string, any>;
    required?: string[];
  };
  output_parameters: {
    properties: Record<string, any>;
  };
  scopes?: string[];
  tags?: string[];
  no_auth: boolean;
}

export interface ComposioToolsResponse {
  success: boolean;
  tools: ComposioTool[];
  total_items: number;
  current_page: number;
  total_pages: number;
  next_cursor?: string;
  error?: string;
}

export interface ComposioToolkitsResponse {
  success: boolean;
  toolkits: ComposioToolkit[];
  total_items: number;
  total_pages: number;
  current_page: number;
  next_cursor?: string;
  has_more: boolean;
  error?: string;
}

export interface ComposioProfile {
  profile_id: string;
  profile_name: string;
  display_name: string;
  toolkit_slug: string;
  toolkit_name: string;
  mcp_url: string;
  redirect_url?: string;
  connected_account_id?: string;
  is_connected: boolean;
  is_default: boolean;
  created_at: string;
}

export interface ComposioProfilesResponse {
  success: boolean;
  profiles: ComposioProfile[];
  error?: string;
}

export interface CreateComposioProfileRequest {
  toolkit_slug: string;
  profile_name: string;
  display_name?: string;
  user_id?: string;
  mcp_server_name?: string;
  is_default?: boolean;
  initiation_fields?: Record<string, string>;
  custom_auth_config?: Record<string, string>;
  use_custom_auth?: boolean;
}

export interface CreateComposioProfileResponse {
  success: boolean;
  profile_id: string;
  redirect_url?: string;
  mcp_url: string;
  error?: string;
}

export interface ComposioMcpConfigResponse {
  success: boolean;
  mcp_config: {
    name: string;
    type: string;
    mcp_qualified_name: string;
    toolkit_slug: string;
    config: {
      profile_id: string;
    };
    enabledTools: string[];
  };
  error?: string;
}

export interface ComposioProfileSummary {
  profile_id: string;
  profile_name: string;
  display_name: string;
  toolkit_slug: string;
  toolkit_name: string;
  is_connected: boolean;
  is_default: boolean;
  created_at: string;
  has_mcp_url: boolean;
}

export interface ComposioToolkitGroup {
  toolkit_slug: string;
  toolkit_name: string;
  icon_url?: string;
  profiles: ComposioProfileSummary[];
}

export interface ComposioCredentialsResponse {
  success: boolean;
  toolkits: ComposioToolkitGroup[];
  total_profiles: number;
}

export interface ComposioMcpUrlResponse {
  success: boolean;
  mcp_url: string;
  profile_name: string;
  toolkit_name: string;
  warning: string;
}

export interface DeleteProfileResponse {
  message: string;
}

export interface BulkDeleteProfilesRequest {
  profile_ids: string[];
}

export interface BulkDeleteProfilesResponse {
  success: boolean;
  deleted_count: number;
  failed_profiles: string[];
  message: string;
}

const normalizeComposioProfile = (profile: ComposioProfile): ComposioProfile => {
  const normalizedToolkitSlug = (profile.toolkit_slug || '').trim().toLowerCase();
  const profileName = profile.profile_name || profile.display_name || 'Profile';
  const displayName = profile.display_name || profile.profile_name || profileName;

  return {
    ...profile,
    toolkit_slug: normalizedToolkitSlug || profile.toolkit_slug,
    profile_name: profileName,
    display_name: displayName,
    is_connected: Boolean(profile.is_connected || profile.mcp_url || profile.connected_account_id),
  };
};

const sortComposioProfiles = (profiles: ComposioProfile[]): ComposioProfile[] => {
  return [...profiles].sort((a, b) => {
    if (a.is_default !== b.is_default) {
      return a.is_default ? -1 : 1;
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
};

const applyProfileFilters = (
  profiles: ComposioProfile[],
  params?: { toolkit_slug?: string; is_active?: boolean },
): ComposioProfile[] => {
  let filtered = profiles;

  if (params?.toolkit_slug) {
    const wantedToolkit = params.toolkit_slug.trim().toLowerCase();
    filtered = filtered.filter((profile) => profile.toolkit_slug === wantedToolkit);
  }

  if (params?.is_active !== undefined) {
    filtered = filtered.filter((profile) => profile.is_connected === params.is_active);
  }

  return filtered;
};

const toComposioProfilesFromCredentials = (
  toolkits: ComposioToolkitGroup[],
): ComposioProfile[] => {
  const profiles = toolkits.flatMap((toolkit) =>
    toolkit.profiles.map((profile) => ({
      profile_id: profile.profile_id,
      profile_name: profile.profile_name,
      display_name: profile.display_name,
      toolkit_slug: profile.toolkit_slug || toolkit.toolkit_slug,
      toolkit_name: profile.toolkit_name || toolkit.toolkit_name,
      mcp_url: '',
      redirect_url: undefined,
      connected_account_id: undefined,
      is_connected: profile.is_connected || profile.has_mcp_url,
      is_default: profile.is_default,
      created_at: profile.created_at,
    })),
  );

  return sortComposioProfiles(profiles.map(normalizeComposioProfile));
};

export const composioApi = {
  async getCategories(): Promise<CompositoCategoriesResponse> {
    const result = await backendApi.get<CompositoCategoriesResponse>(
      '/composio/categories',
      {
        errorContext: { operation: 'load categories', resource: 'Composio categories' },
        timeout: COMPOSIO_REQUEST_TIMEOUT_MS,
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to get categories');
    }

    return result.data!;
  },

  async getToolkits(search?: string, category?: string, cursor?: string, limit: number = 100): Promise<ComposioToolkitsResponse> {
    const params = new URLSearchParams();
    
    if (search) {
      params.append('search', search);
    }
    
    if (category) {
      params.append('category', category);
    }
    
    if (cursor) {
      params.append('cursor', cursor);
    }

    if (limit > 0) {
      params.append('limit', String(limit));
    }
    
    const result = await backendApi.get<ComposioToolkitsResponse>(
      `/composio/toolkits${params.toString() ? `?${params.toString()}` : ''}`,
      {
        errorContext: { operation: 'load toolkits', resource: 'Composio toolkits' },
        timeout: COMPOSIO_REQUEST_TIMEOUT_MS,
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to get toolkits');
    }

    return result.data!;
  },

  async getProfiles(params?: { toolkit_slug?: string; is_active?: boolean }): Promise<ComposioProfile[]> {
    const queryParams = new URLSearchParams();
    
    if (params?.toolkit_slug) {
      queryParams.append('toolkit_slug', params.toolkit_slug);
    }
    
    if (params?.is_active !== undefined) {
      queryParams.append('is_active', params.is_active.toString());
    }
    
    try {
      const result = await backendApi.get<ComposioProfilesResponse>(
        `/composio/profiles${queryParams.toString() ? `?${queryParams.toString()}` : ''}`,
        {
          errorContext: { operation: 'load profiles', resource: 'Composio profiles' },
          timeout: COMPOSIO_REQUEST_TIMEOUT_MS,
        }
      );

      if (!result.success || !result.data) {
        throw new Error(result.error?.message || 'Failed to get profiles');
      }

      const primaryProfiles = sortComposioProfiles(
        (result.data.profiles || []).map(normalizeComposioProfile),
      );

      // If the primary endpoint already reports connected profiles, trust it.
      if (primaryProfiles.some((profile) => profile.is_connected)) {
        return applyProfileFilters(primaryProfiles, params);
      }

      // Otherwise, attempt secure profile fallback and merge connectivity status.
      const fallbackResponse = await backendApi.get<ComposioCredentialsResponse>(
        '/secure-mcp/composio-profiles',
        {
          showErrors: false,
          timeout: COMPOSIO_REQUEST_TIMEOUT_MS,
        },
      );

      if (!fallbackResponse.success || !fallbackResponse.data) {
        return applyProfileFilters(primaryProfiles, params);
      }

      const fallbackProfiles = toComposioProfilesFromCredentials(
        fallbackResponse.data.toolkits || [],
      );
      const fallbackById = new Map(
        fallbackProfiles.map((profile) => [profile.profile_id, profile]),
      );

      const mergedProfiles = primaryProfiles.map((profile) => {
        const fallbackProfile = fallbackById.get(profile.profile_id);
        if (!fallbackProfile) {
          return profile;
        }
        return normalizeComposioProfile({
          ...profile,
          is_connected: profile.is_connected || fallbackProfile.is_connected,
          mcp_url: profile.mcp_url || fallbackProfile.mcp_url,
          connected_account_id:
            profile.connected_account_id || fallbackProfile.connected_account_id,
        });
      });

      const existingIds = new Set(mergedProfiles.map((profile) => profile.profile_id));
      const fallbackOnlyProfiles = fallbackProfiles.filter(
        (profile) => !existingIds.has(profile.profile_id),
      );

      return applyProfileFilters(
        sortComposioProfiles([...mergedProfiles, ...fallbackOnlyProfiles]),
        params,
      );
    } catch (primaryError) {
      // Fallback path for transient /composio/profiles issues:
      // use secure credential profiles so integration cards don't falsely show "Not connected".
      const fallbackResponse = await backendApi.get<ComposioCredentialsResponse>(
        '/secure-mcp/composio-profiles',
        {
          showErrors: false,
          timeout: COMPOSIO_REQUEST_TIMEOUT_MS,
        },
      );

      if (!fallbackResponse.success || !fallbackResponse.data) {
        throw primaryError instanceof Error
          ? primaryError
          : new Error('Failed to get profiles');
      }

      const fallbackProfiles = toComposioProfilesFromCredentials(
        fallbackResponse.data.toolkits || [],
      );
      return applyProfileFilters(fallbackProfiles, params);
    }
  },

  async createProfile(request: CreateComposioProfileRequest): Promise<CreateComposioProfileResponse> {
    const result = await backendApi.post<CreateComposioProfileResponse>(
      '/composio/profiles',
      request,
      {
        errorContext: { operation: 'create profile', resource: 'Composio profile' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to create profile');
    }

    return result.data!;
  },

  async getMcpConfigForProfile(profileId: string): Promise<ComposioMcpConfigResponse> {
    const result = await backendApi.get<ComposioMcpConfigResponse>(
      `/composio/profiles/${profileId}/mcp-config`,
      {
        errorContext: { operation: 'get MCP config', resource: 'Composio profile MCP config' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to get MCP config');
    }

    return result.data!;
  },

  async discoverTools(profileId: string): Promise<{ success: boolean; tools: any[]; toolkit_name: string; total_tools: number }> {
    const result = await backendApi.post<{ success: boolean; tools: any[]; toolkit_name: string; total_tools: number }>(
      `/composio/discover-tools/${profileId}`,
      {},
      {
        errorContext: { operation: 'discover tools', resource: 'Composio profile tools' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to discover tools');
    }

    return result.data!;
  },

  async getCredentialsProfiles(): Promise<ComposioToolkitGroup[]> {
    const response = await backendApi.get<ComposioCredentialsResponse>('/secure-mcp/composio-profiles');
    return response.data.toolkits;
  },

  async getMcpUrl(profileId: string): Promise<ComposioMcpUrlResponse> {
    const response = await backendApi.get<ComposioMcpUrlResponse>(`/secure-mcp/composio-profiles/${profileId}/mcp-url`);
    return response.data;
  },

  async getToolkitIcon(toolkitSlug: string): Promise<{ success: boolean; icon_url?: string }> {
    const response = await backendApi.get<{ success: boolean; toolkit_slug: string; icon_url?: string; message?: string }>(
      `/composio/toolkits/${toolkitSlug}/icon`,
      {
        showErrors: false,
        timeout: 8000,
      }
    );
    if (!response.success || !response.data) {
      return { success: false };
    }
    return {
      success: response.data.success,
      icon_url: response.data.icon_url
    };
  },

  async getToolkitIconsBatch(toolkitSlugs: string[]): Promise<{ success: boolean; icons: Record<string, string> }> {
    const response = await backendApi.post<{ success: boolean; icons: Record<string, string> }>(
      '/composio/toolkits/icons/batch',
      { toolkit_slugs: toolkitSlugs },
      {
        errorContext: { operation: 'get toolkit icons batch', resource: 'Composio toolkit icons' },
        timeout: 10000,
        showErrors: false,
      }
    );
    if (!response.success || !response.data) {
      return {
        success: false,
        icons: {},
      };
    }
    return {
      success: response.data.success,
      icons: response.data.icons || {}
    };
  },

  async getToolkitDetails(toolkitSlug: string): Promise<DetailedComposioToolkitResponse> {
    const result = await backendApi.get<DetailedComposioToolkitResponse>(
      `/composio/toolkits/${toolkitSlug}/details`,
      {
        errorContext: { operation: 'get toolkit details', resource: 'Composio toolkit details' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to get toolkit details');
    }

    return result.data!;
  },

  async getTools(toolkitSlug: string, limit: number = 50): Promise<ComposioToolsResponse> {
    const result = await backendApi.post<ComposioToolsResponse>(
      `/composio/tools/list`,
      {
        toolkit_slug: toolkitSlug,
        limit
      },
      {
        errorContext: { operation: 'get tools', resource: 'Composio tools' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to get tools');
    }

    return result.data!;
  },

  async deleteProfile(profileId: string): Promise<DeleteProfileResponse> {
    const result = await backendApi.delete<DeleteProfileResponse>(
      `/secure-mcp/credential-profiles/${profileId}`,
      {
        errorContext: { operation: 'delete profile', resource: 'Composio profile' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to delete profile');
    }

    return result.data!;
  },

  async bulkDeleteProfiles(profileIds: string[]): Promise<BulkDeleteProfilesResponse> {
    const result = await backendApi.post<BulkDeleteProfilesResponse>(
      '/secure-mcp/credential-profiles/bulk-delete',
      { profile_ids: profileIds },
      {
        errorContext: { operation: 'bulk delete profiles', resource: 'Composio profiles' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to bulk delete profiles');
    }

    return result.data!;
  },

  async setDefaultProfile(profileId: string): Promise<{ message: string }> {
    const result = await backendApi.put<{ message: string }>(
      `/secure-mcp/credential-profiles/${profileId}/set-default`,
      {},
      {
        errorContext: { operation: 'set default profile', resource: 'Composio profile' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to set default profile');
    }

    return result.data!;
  },

  async checkProfileNameAvailability(
    toolkitSlug: string, 
    profileName: string
  ): Promise<{ available: boolean; message: string; suggestions: string[] }> {
    const params = new URLSearchParams({
      toolkit_slug: toolkitSlug,
      profile_name: profileName
    });
    
    const result = await backendApi.get<{ 
      available: boolean; 
      message: string; 
      suggestions: string[] 
    }>(
      `/composio/profiles/check-name-availability?${params.toString()}`,
      {
        errorContext: { operation: 'check profile name', resource: 'Composio profile' },
      }
    );

    if (!result.success) {
      throw new Error(result.error?.message || 'Failed to check profile name availability');
    }

    return result.data!;
  },
}; 
