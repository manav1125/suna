import { backendApi } from "@/lib/api-client";
import { toast } from "@/lib/toast";
import { extractSandboxIdFromSandboxUrl, normalizeSandboxBaseUrl } from "@/lib/utils/url";
import { getAuthTokenWithTimeout } from "@/lib/auth-token";

export enum DownloadFormat {
  PDF = 'pdf',
  PPTX = 'pptx',
  GOOGLE_SLIDES = 'google-slides',
}

export function sanitizePresentationName(name: string): string {
  return name.replace(/[^a-zA-Z0-9\-_]/g, '').toLowerCase();
}

interface FetchPresentationMetadataOptions {
  presentationName: string;
  sandboxUrl?: string;
  sandboxId?: string;
  accessToken?: string;
  signal?: AbortSignal;
}

const PRESENTATION_METADATA_TIMEOUT_MS = 20000;

function getErrorSnippet(text: string): string {
  return text
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 140);
}

function redactSensitiveUrl(url: string): string {
  try {
    const parsed = new URL(url);
    for (const key of ['token', 'access_token', 'authorization']) {
      if (parsed.searchParams.has(key)) {
        parsed.searchParams.set(key, '[redacted]');
      }
    }
    return parsed.toString();
  } catch {
    return url.replace(/([?&](?:token|access_token|authorization)=)[^&]+/gi, '$1[redacted]');
  }
}

function withCacheBust(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.searchParams.set('t', `${Date.now()}`);
    return parsed.toString();
  } catch {
    return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`;
  }
}

function shouldUseDirectSandboxFallback(sandboxUrl: string | undefined): boolean {
  if (!sandboxUrl) return false;
  try {
    const hostname = new URL(sandboxUrl).hostname.toLowerCase();
    // Daytona preview hosts often return HTML warning/interstitial content for direct fetches.
    return !(hostname.includes('daytona') || hostname.includes('proxy'));
  } catch {
    // If URL parsing fails, avoid direct fallback; malformed sandbox URLs should not
    // silently route to a less reliable direct fetch path.
    return false;
  }
}

async function parseJsonResponse(response: Response, sourceUrl: string): Promise<any> {
  const bodyText = await response.text();

  try {
    return JSON.parse(bodyText);
  } catch {
    const snippet = getErrorSnippet(bodyText);
    throw new Error(
      `Expected JSON metadata but got non-JSON response from ${sourceUrl}: ${snippet || 'empty response'}`
    );
  }
}

function isPresentationMetadata(data: any): boolean {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.presentation_name === 'string' &&
    typeof data.slides === 'object' &&
    data.slides !== null
  );
}

/**
 * Load presentation metadata with a resilient strategy:
 * 1. Prefer backend sandbox file API (stable/authenticated path)
 * 2. Fall back to direct sandbox URL for compatibility
 */
export async function fetchPresentationMetadata({
  presentationName,
  sandboxUrl,
  sandboxId,
  accessToken,
  signal,
}: FetchPresentationMetadataOptions): Promise<any> {
  const sanitizedName = sanitizePresentationName(presentationName);
  const errors: string[] = [];
  const candidates: Array<{ url: string; headers?: Record<string, string> }> = [];
  const normalizedSandboxUrl = normalizeSandboxBaseUrl(sandboxUrl);
  const effectiveSandboxId = sandboxId || extractSandboxIdFromSandboxUrl(normalizedSandboxUrl);
  let effectiveAccessToken = accessToken;

  if (!effectiveAccessToken) {
    effectiveAccessToken = (await getAuthTokenWithTimeout(8000)) || undefined;
  }

  const backendBaseUrls = new Set<string>();
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    backendBaseUrls.add(process.env.NEXT_PUBLIC_BACKEND_URL);
  }
  if (typeof window !== 'undefined') {
    // Fallback for deployments that proxy backend under /v1 on the same origin.
    backendBaseUrls.add('/v1');
  }

  if (effectiveSandboxId) {
    for (const backendUrl of backendBaseUrls) {
      try {
        const normalizedBackendUrl = backendUrl.startsWith('http')
          ? backendUrl
          : `${typeof window !== 'undefined' ? window.location.origin : ''}${backendUrl.startsWith('/') ? '' : '/'}${backendUrl}`;
        const apiUrl = new URL(`${normalizedBackendUrl.replace(/\/+$/, '')}/sandboxes/${effectiveSandboxId}/files/content`);
        apiUrl.searchParams.append('path', `/workspace/presentations/${sanitizedName}/metadata.json`);
        apiUrl.searchParams.append('inline', 'true');
        // Query token avoids CORS preflight/header stripping issues in iframe/fetch contexts.
        if (effectiveAccessToken) {
          apiUrl.searchParams.append('token', effectiveAccessToken);
        }
        candidates.push({ url: apiUrl.toString() });

        // Keep an Authorization-header fallback for environments where query token is disabled.
        if (effectiveAccessToken) {
          const headerAuthUrl = new URL(apiUrl.toString());
          headerAuthUrl.searchParams.delete('token');
          candidates.push({
            url: headerAuthUrl.toString(),
            headers: { Authorization: `Bearer ${effectiveAccessToken}` },
          });
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        errors.push(`invalid backend URL (${backendUrl}): ${message}`);
      }
    }
  }

  // Keep direct sandbox metadata URL only for non-Daytona hosts.
  if (normalizedSandboxUrl && (candidates.length === 0 || shouldUseDirectSandboxFallback(normalizedSandboxUrl))) {
    candidates.push({ url: `${normalizedSandboxUrl}/presentations/${sanitizedName}/metadata.json` });
  }

  const executeCandidate = async (candidate: { url: string; headers?: Record<string, string> }) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), PRESENTATION_METADATA_TIMEOUT_MS);
    let abortedByParent = false;

    const abortFromParent = () => {
      abortedByParent = true;
      controller.abort();
    };

    if (signal) {
      if (signal.aborted) {
        abortFromParent();
      } else {
        signal.addEventListener('abort', abortFromParent, { once: true });
      }
    }

    try {
      const response = await fetch(withCacheBust(candidate.url), {
        cache: 'no-store',
        signal: controller.signal,
        headers: candidate.headers,
      });
      return response;
    } finally {
      clearTimeout(timeout);
      if (signal) {
        signal.removeEventListener('abort', abortFromParent);
      }
      if (abortedByParent) {
        throw new Error('Request cancelled');
      }
    }
  };

  for (const candidate of candidates) {
    const safeUrl = redactSensitiveUrl(candidate.url);
    try {
      const response = await executeCandidate(candidate);

      if (!response.ok) {
        const errText = await response.text().catch(() => '');
        errors.push(`${safeUrl} -> HTTP ${response.status}${errText ? ` (${getErrorSnippet(errText)})` : ''}`);
        continue;
      }

      const parsed = await parseJsonResponse(response, safeUrl);
      if (!isPresentationMetadata(parsed)) {
        const detail = typeof parsed?.detail === 'string' ? parsed.detail : 'unexpected JSON shape';
        errors.push(`${safeUrl} -> invalid metadata payload (${detail})`);
        continue;
      }

      return parsed;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      errors.push(`${safeUrl} -> ${message}`);
    }
  }

  throw new Error(`Failed to load presentation metadata. ${errors.join(' | ')}`);
}

/**
 * Utility functions for handling presentation slide file paths
 */

/**
 * Gets the PDF URL for a presentation template
 * @param templateId - The template ID
 * @returns The full PDF URL with parameters
 */
export const getPdfUrl = (templateId: string): string => {
  const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";
  return `${API_URL}/presentation-templates/${templateId}/pdf#toolbar=0&navpanes=0&scrollbar=0&view=FitH`;
};

/**
 * Gets the image URL for a presentation template
 * @param templateId - The template ID
 * @param hasImage - Whether the template has an image
 * @returns The full image URL
 */
export const getImageUrl = (templateId: string, hasImage: boolean): string => {
  const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";
  return `${API_URL}/presentation-templates/${templateId}/image.png`;
};

/**
 * Validates and extracts presentation info from a file path in a single operation
 * @param filePath - The file path to validate and extract information from
 * @returns Object containing validation result and extracted data
 */
export function parsePresentationSlidePath(filePath: string | null): {
  isValid: boolean;
  presentationName: string | null;
  slideNumber: number | null;
} {
  if (!filePath) {
    return { isValid: false, presentationName: null, slideNumber: null };
  }
  
  // Match patterns like:
  // - presentations/[name]/slide_01.html
  // - /workspace/presentations/[name]/slide_01.html
  // - ./presentations/[name]/slide_01.html
  // - any/path/presentations/[name]/slide_01.html
  const match = filePath.match(/presentations\/([^\/]+)\/slide_(\d+)\.html$/i);
  if (match) {
    return {
      isValid: true,
      presentationName: match[1],
      slideNumber: parseInt(match[2], 10)
    };
  }
  
  return { isValid: false, presentationName: null, slideNumber: null };
}

/**
 * Creates modified tool content for PresentationViewer from presentation slide data
 * @param presentationName - Name of the presentation
 * @param filePath - Path to the slide file
 * @param slideNumber - Slide number
 * @returns JSON stringified tool content that matches expected structure for PresentationViewer
 */
export function createPresentationViewerToolContent(
  presentationName: string,
  filePath: string,
  slideNumber: number
): string {
  // PresentationViewer expects presentation_path to be the directory, not the file
  // e.g., "presentations/mypresentation" not "presentations/mypresentation/slide_01.html"
  const presentationPath = `presentations/${presentationName}`;
  
  // Return a flat structure that PresentationViewer can directly parse
  const toolOutput = {
    presentation_name: presentationName,
    presentation_path: presentationPath,
    slide_number: slideNumber,
    slide_file: filePath,
    presentation_title: presentationName,
    message: `Slide ${slideNumber} edited successfully`
  };

  return JSON.stringify(toolOutput);
}

/**
 * Downloads a presentation as PDF or PPTX
 * @param sandboxUrl - The sandbox URL for the API endpoint
 * @param presentationPath - The path to the presentation in the workspace
 * @param presentationName - The name of the presentation for the downloaded file
 * @param format - The format to download the presentation as
 * @returns Promise that resolves when download is complete
 */
export async function downloadPresentation(
  format: DownloadFormat,
  sandboxUrl: string, 
  presentationPath: string, 
  presentationName: string
): Promise<void> {
  try {
    const normalizedSandboxUrl = normalizeSandboxBaseUrl(sandboxUrl);
    if (!normalizedSandboxUrl) {
      throw new Error('Invalid sandbox URL');
    }
    const endpoint = `${normalizedSandboxUrl}/presentation/convert-to-${format}`;
    console.log(`[downloadPresentation] Requesting download:`, {
      endpoint,
      format,
      presentationPath,
      presentationName,
      sandboxUrl: normalizedSandboxUrl
    });

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        presentation_path: presentationPath,
        download: true
      })
    });
    
    console.log(`[downloadPresentation] Response status:`, {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      headers: Object.fromEntries(response.headers.entries())
    });

    if (!response.ok) {
      // Try to get error details from response
      let errorMessage = `Failed to download ${format}`;
      let errorDetail = '';
      
      try {
        const errorText = await response.text();
        console.error(`[downloadPresentation] Error response body:`, errorText);
        
        // Try to parse as JSON
        try {
          const errorJson = JSON.parse(errorText);
          errorDetail = errorJson.detail || errorJson.message || errorText;
        } catch {
          errorDetail = errorText || response.statusText;
        }
      } catch (e) {
        console.error(`[downloadPresentation] Failed to read error response:`, e);
        errorDetail = response.statusText;
      }
      
      errorMessage = errorDetail 
        ? `${errorMessage}: ${errorDetail} (HTTP ${response.status})`
        : `${errorMessage} (HTTP ${response.status})`;
      
      console.error(`[downloadPresentation] Error:`, {
        status: response.status,
        statusText: response.statusText,
        errorDetail,
        errorMessage
      });
      
      toast.error(errorMessage, {
        duration: 10000,
      });
      
      throw new Error(errorMessage);
    }
    
    // Check if response is actually a PDF/PPTX blob
    const contentType = response.headers.get('content-type');
    console.log(`[downloadPresentation] Response content type:`, contentType);
    
    if (!contentType || (!contentType.includes('pdf') && !contentType.includes('presentation'))) {
      // If not a binary file, might be an error JSON response
      const text = await response.text();
      console.error(`[downloadPresentation] Unexpected content type, response:`, text);
      
      try {
        const json = JSON.parse(text);
        const errorMsg = json.detail || json.message || `Unexpected response format`;
        toast.error(`Download failed: ${errorMsg}`, {
          duration: 10000,
        });
        throw new Error(errorMsg);
      } catch {
        throw new Error(`Unexpected response format. Expected PDF/PPTX but got ${contentType}`);
      }
    }
    
    const blob = await response.blob();
    console.log(`[downloadPresentation] Blob created:`, {
      size: blob.size,
      type: blob.type
    });
    
    if (blob.size === 0) {
      throw new Error(`Downloaded file is empty`);
    }
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${presentationName}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    console.log(`[downloadPresentation] Download completed successfully`);
    toast.success(`Downloaded ${presentationName} as ${format.toUpperCase()}`, {
      duration: 8000,
    });
  } catch (error) {
    console.error(`[downloadPresentation] Error downloading ${format}:`, error);
    
    // Only show toast if it's not already shown (to avoid duplicate toasts)
    if (error instanceof Error && !error.message.includes('Failed to download')) {
      toast.error(`Failed to download ${format.toUpperCase()}: ${error.message}`, {
        duration: 10000,
      });
    }
    
    throw error; // Re-throw to allow calling code to handle
  }
}

export const handleGoogleAuth = async (presentationPath: string, sandboxUrl: string) => {
  try {
    const normalizedSandboxUrl = normalizeSandboxBaseUrl(sandboxUrl);
    if (!normalizedSandboxUrl) {
      throw new Error('Invalid sandbox URL');
    }
    // Store intent to upload to Google Slides after OAuth
    sessionStorage.setItem('google_slides_upload_intent', JSON.stringify({
      presentation_path: presentationPath,
      sandbox_url: normalizedSandboxUrl
    }));
    
    // Pass the current URL to the backend so it can be included in the OAuth state
    const currentUrl = encodeURIComponent(window.location.href);
    const response = await backendApi.get(`/google/auth-url?return_url=${currentUrl}`);
    
    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to get auth URL');
    }
    
    const { auth_url } = response.data;
    
    if (auth_url) {
      window.location.href = auth_url;
      return;
    }
  } catch (error) {
    console.error('Error initiating Google auth:', error);
    toast.error('Failed to initiate Google authentication');
  }
};


export const handleGoogleSlidesUpload = async (sandboxUrl: string, presentationPath: string) => {
  if (!sandboxUrl || !presentationPath) {
    throw new Error('Missing required parameters');
  }
  
  try {
    const normalizedSandboxUrl = normalizeSandboxBaseUrl(sandboxUrl);
    if (!normalizedSandboxUrl) {
      throw new Error('Invalid sandbox URL');
    }

    const accessToken = await getAuthTokenWithTimeout(8000);
    if (!accessToken) {
      throw new Error('Authentication required');
    }
    
    // Use proper backend API client with authentication and extended timeout for PPTX generation
    const response = await backendApi.post('/presentation-tools/convert-and-upload-to-slides', {
      presentation_path: presentationPath,
      sandbox_url: normalizedSandboxUrl,
    }, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
      timeout: 180000, // 3 minutes timeout for PPTX generation (longer than backend's 2 minute timeout)
    });

    if (!response.success) {
      throw new Error('Failed to upload to Google Slides');
    }

    const result = response.data;
    
    if (!result.success && !result.is_api_enabled) {
      toast.info('Redirecting to Google authentication...', {
        duration: 3000,
      });
      handleGoogleAuth(presentationPath, normalizedSandboxUrl);
      return {
        success: false,
        redirected_to_auth: true,
        message: 'Redirecting to Google authentication'
      };
    }
    
    if (result.google_slides_url) {
      // Always show rich success toast - this is universal
      toast.success('🎉 Presentation uploaded successfully!', {
        action: {
          label: 'Open in Google Slides',
          onClick: () => window.open(result.google_slides_url, '_blank'),
        },
        duration: 20000,
      });
      
      // Extract presentation name from path for display
      const presentationName = presentationPath.split('/').pop() || 'presentation';
      
      return {
        success: true,
        google_slides_url: result.google_slides_url,
        message: `"${presentationName}" uploaded successfully`
      };
    } 
    
    // Only throw error if no Google Slides URL was returned
    throw new Error(result.message || 'No Google Slides URL returned');
    
  } catch (error) {
    console.error('Error uploading to Google Slides:', error);
    
    // Show error toasts - this is also universal
    if (error instanceof Error && error.message.includes('not authenticated')) {
      toast.error('Please authenticate with Google first');
    } else {
      toast.error('Failed to upload to Google Slides');
    }
    
    // Re-throw for any calling code that needs to handle it
    throw error;
  }
};
