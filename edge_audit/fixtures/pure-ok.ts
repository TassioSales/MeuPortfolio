export function extractBaseEmail(email: string): string {
  if (!email.includes("@")) {
    return email;
  }
  const [localPart, ...domainParts] = email.split("@");
  return `${localPart?.split("+")[0] ?? ""}@${domainParts.join("@")}`;
}

export function stripMarkdown(markdown: string): string {
  return markdown.replace(/[*_`#]/g, "");
}
