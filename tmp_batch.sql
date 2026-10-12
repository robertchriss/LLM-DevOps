```sql
INSERT INTO lessons (slug, title, content) VALUES ('network-policies', 'NetworkPolicies & Pod Security', '
# Kubernetes NetworkPolicies & Pod Security

## Introduction
In Kubernetes, managing network policies and ensuring secure pod operations are essential for robust and secure container environments. This lesson covers the basics of NetworkPolicies and Pod Security in Kubernetes.

## NetworkPolicies
NetworkPolicies in Kubernetes are used to implement network access control between pods, services, and external IP addresses. They allow you to specify which pods can communicate with each other, providing a finer level of control over your cluster''s network traffic.

### Example of a NetworkPolicy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-egress-to-external
spec:
  podSelector:
    matchLabels:
      app: myapp
  egress:
  - to:
    - ipBlock:
        cidr: 8.8.8.8/32
    ports:
    - protocol: TCP
      port: 53
```

## Pod Security
Pod Security policies in Kubernetes provide a way to enforce security requirements for pods running in a cluster. They can restrict the allowed capabilities, host access, and resource requests/limits for pods.

### Example of a PodSecurityPolicy
```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted
spec:
  allowedCapabilities:
  - SYS_ADMIN
  defaultAddCapabilities: []
  fsGroup:
    rule: RunAsAny
  runAsUser:
    rule: MustRunAs
  seLinux:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
  volumes:
  - '*'
```

## Conclusion
Understanding and correctly implementing NetworkPolicies and Pod Security policies are crucial steps towards securing your Kubernetes environment. Familiarizing yourself with the examples provided here will help you better manage and secure your deployments.
');

INSERT INTO quizzes (lesson_id, question, options, correct_index, explanation) VALUES 
((SELECT id FROM lessons WHERE slug='network-policies'), 'What does a NetworkPolicy in Kubernetes define?', '["Network traffic rules between pods", "Volume mounting rules", "Pod lifecycle events", "Namespace access control rules"]'::jsonb, 0, 'A NetworkPolicy defines network traffic rules between pods, services, and external IP addresses in a Kubernetes cluster.');

INSERT INTO quizzes (lesson_id, question, options, correct_index, explanation) VALUES 
((SELECT id FROM lessons WHERE slug='network-policies'), 'Which Kubernetes API version is used for PodSecurityPolicy?', '["policy/v1beta1", "networking.k8s.io/v1", "extensions/v1beta1", "policy/v1"]'::jsonb, 0, 'The PodSecurityPolicy API version is policy/v1beta1.');

INSERT INTO quizzes (lesson_id, question, options, correct_index, explanation) VALUES 
((SELECT id FROM lessons WHERE slug='network-policies'), 'What is the purpose of a PodSecurityPolicy?', '["To define network policies", "To enforce security requirements for pods", "To manage pod lifecycle events", "To control volume mounts"]'::jsonb, 1, 'A PodSecurityPolicy is used to enforce security requirements for pods, including allowed capabilities, host access, and resource requests/limits.');
```