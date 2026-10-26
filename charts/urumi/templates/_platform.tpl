{{- define "urumi.platformLabels" -}}
{{ include "urumi.selectorLabels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "urumi.platformImage" -}}
{{- printf "%s:%s" .repository .tag -}}
{{- end -}}

{{- define "urumi.platformSecurity" -}}
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "urumi.platformContainerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end -}}

{{- define "urumi.databaseEnv" -}}
- name: URUMI_DATABASE_URL_FILE
  value: /run/secrets/postgres/database-url
{{- end -}}

{{- define "urumi.databaseMount" -}}
- name: postgres-auth
  mountPath: /run/secrets/postgres
  readOnly: true
{{- end -}}

{{- define "urumi.databaseVolume" -}}
- name: postgres-auth
  secret:
    secretName: {{ .Values.platform.postgres.secretName | quote }}
    defaultMode: 0440
    items:
      - key: database-url
        path: database-url
{{- end -}}
