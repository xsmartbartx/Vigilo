import { OG_SIZE, socialImage } from "../lib/og";
import { brand } from "../lib/brand";

export const alt = `${brand.name}: ${brand.shortDescription}`;
export const size = OG_SIZE;
export const contentType = "image/png";

export default function Image() {
  return socialImage(
    brand.name,
    `Other scanners bury you in alerts. ${brand.name} shows only what it can prove.`,
    brand.shortDescription,
  );
}
