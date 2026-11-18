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

{{- define "urumi.credentialEnv" -}}
- {name: URUMI_NAMESPACE, value: {{ .Release.Namespace | quote }}}
- {name: URUMI_UPSTREAM_SECRET_NAME, value: {{ printf "%s-upstream-credentials" (include "urumi.fullname" .) | quote }}}
{{- end -}}
{{- define "urumi.credentialMount" -}}
- {name: kubernetes-auth, mountPath: /run/kubernetes, readOnly: true}
{{- end -}}
{{- define "urumi.credentialVolume" -}}
- name: kubernetes-auth
  projected:
    defaultMode: 0440
    sources:
      - serviceAccountToken: {path: token, expirationSeconds: 3600}
      - configMap:
          name: kube-root-ca.crt
          items: [{key: ca.crt, path: ca.crt}]
{{- end -}}
