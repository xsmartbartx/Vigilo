import { ImageResponse } from "next/og";

// PLACEHOLDER (see app/icon.svg). Opaque background: iOS rejects transparency.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#09090B",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        <div
          style={{
            width: 80,
            height: 80,
            borderRadius: 40,
            border: "14px solid #818CF8",
            display: "flex",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 46,
            left: 108,
            width: 24,
            height: 24,
            borderRadius: 12,
            background: "#818CF8",
            display: "flex",
          }}
        />
      </div>
    ),
    { ...size },
  );
}
