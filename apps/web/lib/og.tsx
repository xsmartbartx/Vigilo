import { ImageResponse } from "next/og";

// PLACEHOLDER social image: text on the brand's dark background. Replace with
// designed artwork when the logo exists (replica/brand.md has the brief).
export const OG_SIZE = { width: 1200, height: 630 };

export function socialImage(eyebrow: string, headline: string, footer: string) {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#09090B",
          color: "#F4F4F5",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
        }}
      >
        <div style={{ fontSize: 34, color: "#818CF8", display: "flex" }}>{eyebrow}</div>
        <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.1, display: "flex" }}>
          {headline}
        </div>
        <div style={{ fontSize: 30, color: "#A1A1AA", display: "flex" }}>{footer}</div>
      </div>
    ),
    { ...OG_SIZE },
  );
}
