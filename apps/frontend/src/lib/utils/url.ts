interface HtmlPreviewUrlOptions {
  sandboxId?: string;
  accessToken?: string;
  preferBackendProxy?: boolean;
  inline?: boolean;
  backendUrl?: string;
}

export function normalizeSandboxBaseUrl(sandboxUrl: string | undefined): string | undefined {
  if (!sandboxUrl) return undefined;

  try {
    const parsed = new URL(sandboxUrl);
    const hostname = parsed.hostname.toLowerCase();
    const isDaytonaHost = hostname.includes('daytona');
    const isProxyHost = hostname.includes('proxy');

    if (parsed.protocol === 'http:' && (isDaytonaHost || isProxyHost)) {
      parsed.protocol = 'https:';
      return parsed.toString().replace(/\/+$/, '');
    }

    return sandboxUrl.replace(/\/+$/, '');
  } catch {
    return sandboxUrl.replace(/\/+$/, '');
  }
}

export function extractSandboxIdFromSandboxUrl(sandboxUrl: string | undefined): string | undefined {
  if (!sandboxUrl) return undefined;

  const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i;

  try {
    const parsed = new URL(sandboxUrl);
    const hostname = parsed.hostname.toLowerCase();
    const isDaytonaHost = hostname.includes('daytona');
    const firstLabel = parsed.hostname.split('.')[0];
    if (!firstLabel) return undefined;

    // Daytona preview host commonly uses "<port>-<sandbox-id>.<domain>"
    const portPrefixedMatch = firstLabel.match(/^\d+-(.+)$/);
    if (portPrefixedMatch?.[1] && isDaytonaHost) {
      return portPrefixedMatch[1];
    }

    // Fallback for sandbox-id-like host labels on Daytona domains.
    if (isDaytonaHost) {
      const plainIdMatch = firstLabel.match(/^[a-zA-Z0-9-]{8,}$/);
      if (plainIdMatch) {
        return firstLabel;
      }
    }

    // Fallback for UUID-looking host labels on non-Daytona custom domains.
    const hostUuidMatch = firstLabel.match(uuidRegex);
    if (hostUuidMatch?.[0]) return hostUuidMatch[0];
  } catch {
    // no-op
  }

  const rawUuidMatch = sandboxUrl.match(uuidRegex);
  return rawUuidMatch?.[0];
}

function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function extractWorkspacePathFromFilePath(filePath: string): string | undefined {
  let processedPath = filePath;

  // If filePath is a full URL (API endpoint), extract the path parameter
  if (
    filePath.includes('://') ||
    filePath.includes('/sandboxes/') ||
    filePath.includes('/files/content') ||
    filePath.includes('/preview/')
  ) {
    try {
      if (filePath.includes('://')) {
        const url = new URL(filePath);
        const pathParam = url.searchParams.get('path');
        if (pathParam) {
          processedPath = safeDecodeURIComponent(pathParam);
        } else {
          // Handle direct preview URLs like:
          // https://8080-<sandbox>.daytonaproxy01.net/presentations/foo/slide_01.html
          const pathname = safeDecodeURIComponent(url.pathname || '');

          if (pathname.startsWith('/workspace/')) {
            processedPath = pathname;
          } else if (pathname.startsWith('/presentations/')) {
            processedPath = pathname;
          } else {
            const workspaceIndex = pathname.indexOf('/workspace/');
            const presentationsIndex = pathname.indexOf('/presentations/');

            if (workspaceIndex >= 0) {
              processedPath = pathname.slice(workspaceIndex);
            } else if (presentationsIndex >= 0) {
              processedPath = pathname.slice(presentationsIndex);
            } else {
              const pathMatch = filePath.match(/[?&]path=([^&]+)/);
              if (pathMatch) {
                processedPath = safeDecodeURIComponent(pathMatch[1]);
              } else {
                const sandboxMatch = filePath.match(/\/sandboxes\/[^\/]+\/files\/content[?&]path=([^&]+)/);
                if (sandboxMatch) {
                  processedPath = safeDecodeURIComponent(sandboxMatch[1]);
                } else if (
                  pathname.endsWith('.html') ||
                  pathname.endsWith('.htm') ||
                  pathname.endsWith('.json')
                ) {
                  processedPath = pathname;
                } else {
                  return undefined;
                }
              }
            }
          }
        }
      } else {
        const pathMatch = filePath.match(/[?&]path=([^&]+)/);
        if (pathMatch) {
          processedPath = safeDecodeURIComponent(pathMatch[1]);
        } else {
          return undefined;
        }
      }
    } catch {
      // If URL parsing fails, treat as regular path
    }
  }

  // Normalize to /workspace/... because backend file API expects workspace-absolute paths.
  if (processedPath === 'workspace' || processedPath.startsWith('workspace/')) {
    processedPath = `/${processedPath}`;
  } else if (!processedPath.startsWith('/workspace')) {
    processedPath = `/workspace/${processedPath.replace(/^\/+/, '')}`;
  }

  return processedPath;
}

function normalizeBackendBaseUrl(backendUrl?: string): string | undefined {
  const raw =
    backendUrl ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    (typeof window !== 'undefined' ? `${window.location.origin}/v1` : undefined);

  if (!raw) return undefined;

  if (raw.startsWith('http')) {
    return raw.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    return `${window.location.origin}${raw.startsWith('/') ? '' : '/'}${raw}`.replace(/\/+$/, '');
  }

  return undefined;
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
  const normalizedSandboxUrl = normalizeSandboxBaseUrl(sandboxUrl);
  if (!normalizedSandboxUrl || !filePath) {
    return undefined;
  }

  const workspacePath = extractWorkspacePathFromFilePath(filePath);
  if (!workspacePath) {
    return undefined;
  }

  const effectiveSandboxId = options?.sandboxId || extractSandboxIdFromSandboxUrl(normalizedSandboxUrl);
  if (options?.preferBackendProxy && effectiveSandboxId) {
    const backendBase = normalizeBackendBaseUrl(options.backendUrl);
    if (backendBase) {
      try {
        const proxyPath = workspacePath
          .replace(/^\/+/, '')
          .split('/')
          .filter(Boolean)
          .map((segment) => encodeURIComponent(segment))
          .join('/');
        if (!proxyPath) return undefined;

        const proxyUrl = new URL(`${backendBase}/sandboxes/${effectiveSandboxId}/preview/${proxyPath}`);
        if (options.accessToken) {
          proxyUrl.searchParams.set('token', options.accessToken);
        }
        return proxyUrl.toString();
      } catch {
        // Fall through to direct sandbox preview URL.
      }
    }
  }

  let processedPath = workspacePath;
  // Remove /workspace/ prefix for direct sandbox path rendering.
  processedPath = processedPath.replace(/^\/workspace\//, '');

  const pathSegments = processedPath
    .split('/')
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment));

  const encodedPath = pathSegments.join('/');

  return `${normalizedSandboxUrl}/${encodedPath}`;
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
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`;
  }
}
