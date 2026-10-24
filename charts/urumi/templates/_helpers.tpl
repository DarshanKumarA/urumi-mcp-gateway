{{/* Leave room for component suffixes in DNS-compatible resource names. */}}
{{- define "urumi.fullname" -}}
{{- .Release.Name | trunc 53 | trimSuffix "-" -}}
{{- end -}}

{{- define "urumi.wordpressName" -}}
{{- printf "%s-wordpress" (include "urumi.fullname" .) -}}
{{- end -}}

{{- define "urumi.mariadbName" -}}
{{- printf "%s-mariadb" (include "urumi.fullname" .) -}}
{{- end -}}

{{- define "urumi.wooMcpName" -}}
{{- printf "%s-woo-mcp" (include "urumi.fullname" .) -}}
{{- end -}}

{{/* Exact Host forms for server-side clients; no wildcard hosts or browser Origins. */}}
{{- define "urumi.wooMcpAllowedHosts" -}}
{{- if .Values.wooMcp.config.allowed_hosts -}}
{{- join "," .Values.wooMcp.config.allowed_hosts -}}
{{- else -}}
{{- $name := include "urumi.wooMcpName" . -}}
{{- $names := list $name (printf "%s.%s" $name .Release.Namespace) (printf "%s.%s.svc" $name .Release.Namespace) (printf "%s.%s.svc.cluster.local" $name .Release.Namespace) "127.0.0.1" "localhost" -}}
{{- $hosts := list -}}
{{- range $names -}}
{{- $hosts = append $hosts . -}}
{{- $hosts = append $hosts (printf "%s:8000" .) -}}
{{- end -}}
{{- join "," $hosts -}}
{{- end -}}
{{- end -}}

{{/* Selectors deliberately exclude chart version and other mutable labels. */}}
{{- define "urumi.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
{{- end -}}

{{- define "urumi.labels" -}}
{{ include "urumi.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" | quote }}
{{- end -}}
