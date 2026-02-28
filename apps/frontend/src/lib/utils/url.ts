interface HtmlPreviewUrlOptions {
  sandboxId?: string;
  accessToken?: string;
  preferBackendProxy?: boolean;
  inline?: boolean;
}

function extractWorkspacePathFromFilePath(filePath: string): string | undefined {
  let processedPath = filePath;

  // If filePath is a full URL (API endpoint), extract the path parameter
  if (filePath.includes('://') || filePath.includes('/sandboxes/') || filePath.includes('/files/content')) {
    try {
      // Try to parse as URL if it's a full URL
      if (filePath.includes('://')) {
        const url = new URL(filePath);
        const pathParam = url.searchParams.get('path');
        if (pathParam) {
          processedPath = decodeURIComponent(pathParam);
        } else {
          // If no path param, try to extract from pathname
          // Handle patterns like /v1/sandboxes/.../files/content?path=...
          const pathMatch = filePath.match(/[?&]path=([^&]+)/);
          if (pathMatch) {
            processedPath = decodeURIComponent(pathMatch[1]);
          } else {
            // If it's a relative URL with /sandboxes/ pattern, extract the path
            const sandboxMatch = filePath.match(/\/sandboxes\/[^\/]+\/files\/content[?&]path=([^&]+)/);
            if (sandboxMatch) {
              processedPath = decodeURIComponent(sandboxMatch[1]);
            } else {
              // Can't extract path
              return undefined;
            }
          }
        }
      } else {
        // Relative URL pattern: /sandboxes/.../files/content?path=...
        const pathMatch = filePath.match(/[?&]path=([^&]+)/);
        if (pathMatch) {
          processedPath = decodeURIComponent(pathMatch[1]);
        } else {
          // Can't extract path
          return undefined;
        }
      }
    } catch (e) {
      // If URL parsing fails, treat as regular path
      console.warn('Failed to parse filePath as URL, treating as regular path:', filePath);
    }
  }

  // Normalize to /workspace/... because backend file API expects workspace-absolute paths.
  if (!processedPath.startsWith('/workspace')) {
    processedPath = `/workspace/${processedPath.replace(/^\/+/, '')}`;
  }

  return processedPath;
}

/**
 * Constructs a preview URL for HTML files in the sandbox environment.
 * Properly handles URL encoding of file paths by encoding each path segment individually.
 *
 * @param sandboxUrl - The base URL of the sandbox
 * @param filePath - The path to the HTML file (can include /workspace/ prefix, or be a full API URL)
 * @param options - Optional URL construction behavior
 * @returns The properly encoded preview URL, or undefined if inputs are invalid
 */
export function constructHtmlPreviewUrl(
  sandboxUrl: string | undefined,
  filePath: string | undefined,
  options?: HtmlPreviewUrlOptions,
): string | undefined {
  if (!sandboxUrl || !filePath) {
    return undefined;
  }

  const workspacePath = extractWorkspacePathFromFilePath(filePath);
  if (!workspacePath) {
    return undefined;
  }

  if (options?.preferBackendProxy && options.sandboxId && options.accessToken) {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || '';
    if (backendUrl) {
      try {
        const normalizedBackendUrl = backendUrl.startsWith('http')
          ? backendUrl
          : `${typeof window !== 'undefined' ? window.location.origin : ''}${backendUrl.startsWith('/') ? '' : '/'}${backendUrl}`;
        const apiUrl = new URL(`${normalizedBackendUrl.replace(/\/+$/, '')}/sandboxes/${options.sandboxId}/files/content`);
        apiUrl.searchParams.append('path', workspacePath);
        apiUrl.searchParams.append('token', options.accessToken);
        if (options.inline !== false) {
          apiUrl.searchParams.append('inline', 'true');
        }
        return apiUrl.toString();
      } catch (e) {
        console.warn('Failed to build backend HTML preview URL, falling back to sandbox URL:', e);
      }
    }
  }

  let processedPath = workspacePath;

  // Remove /workspace/ prefix if present
  processedPath = processedPath.replace(/^\/workspace\//, '');

  // Split the path into segments and encode each segment individually
  const pathSegments = processedPath
    .split('/')
    .filter(Boolean) // Remove empty segments
    .map((segment) => encodeURIComponent(segment));

  // Join the segments back together with forward slashes
  const encodedPath = pathSegments.join('/');

  return `${sandboxUrl}/${encodedPath}`;
}

/**
 * Safely append or replace a query param on a URL string.
 */
export function withQueryParam(
  url: string | undefined,
  key: string,
  value: string | number | boolean,
): string | undefined {
  if (!url) return undefined;

  try {
    const parsed = new URL(url);
    parsed.searchParams.set(key, String(value));
    return parsed.toString();
  } catch {
    // Fallback for malformed or relative URLs
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`;
  }
}
