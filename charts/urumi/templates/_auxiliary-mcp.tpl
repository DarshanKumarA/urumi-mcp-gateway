{{/* Stateless auxiliaries share templates; keep resource names within DNS limits. */}}
{{- define "urumi.auxiliaryMcpName" -}}
{{- $prefix := .root.Release.Name | trunc (int (sub 62 (len .component))) | trimSuffix "-" -}}
{{- printf "%s-%s" $prefix .component -}}
{{- end -}}

{{- define "urumi.auxiliaryMcpHosts" -}}
{{- $name := include "urumi.auxiliaryMcpName" . -}}
{{- $ns := .root.Release.Namespace -}}
{{- $hosts := list -}}
{{- range list $name (printf "%s.%s" $name $ns) (printf "%s.%s.svc" $name $ns) (printf "%s.%s.svc.cluster.local" $name $ns) "127.0.0.1" "localhost" -}}
{{- $hosts = append $hosts . -}}
{{- $hosts = append $hosts (printf "%s:8000" .) -}}
{{- end -}}
{{- join "," $hosts -}}
{{- end -}}
