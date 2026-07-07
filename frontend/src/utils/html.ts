// Steam 게임 메타데이터(설명·제목·장르)는 Steam 스토어의 HTML 텍스트에서 왔기 때문에
// &quot; &amp; &#39; 같은 HTML 엔티티를 raw 문자열로 포함한다. React는 텍스트 노드를
// 렌더할 때 엔티티를 디코드하지 않으므로(그대로 "&quot;"로 보임), 표시 직전에 디코드한다.
// 결과는 React 텍스트 노드로만 렌더되므로(=innerHTML 아님) XSS 위험은 없다.

const NAMED_ENTITIES: Record<string, string> = {
  quot: '"',
  amp: "&",
  apos: "'",
  lt: "<",
  gt: ">",
  nbsp: " ",
  reg: "®",
  copy: "©",
  trade: "™",
  hellip: "…",
  mdash: "—",
  ndash: "–",
  lsquo: "‘",
  rsquo: "’",
  ldquo: "“",
  rdquo: "”",
};

/** HTML 엔티티(명명 + 10진/16진 숫자)를 디코드한다. null/undefined는 빈 문자열로. */
export function decodeHtmlEntities(input: string | null | undefined): string {
  if (!input) return "";
  return input.replace(
    /&(#x?[0-9a-f]+|[a-z][a-z0-9]*);/gi,
    (match, code: string) => {
      if (code[0] === "#") {
        const isHex = code[1] === "x" || code[1] === "X";
        const num = parseInt(code.slice(isHex ? 2 : 1), isHex ? 16 : 10);
        if (Number.isFinite(num) && num >= 0 && num <= 0x10ffff) {
          return String.fromCodePoint(num);
        }
        return match;
      }
      return NAMED_ENTITIES[code.toLowerCase()] ?? match;
    },
  );
}
