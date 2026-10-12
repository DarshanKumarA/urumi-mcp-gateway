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
