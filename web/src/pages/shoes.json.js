// Build-time JSON index of every shoe — powers client-side search and compare.
import { getShoes } from "../lib/shoes.js";

const FIELDS = [
  "slug", "name", "brand", "archetype", "msrp_usd", "image_url",
  "runhub_score", "category_rank", "value_rating",
  "score_ride", "score_cushioning", "score_weight",
  "score_comfort_fit", "score_durability", "score_expert",
  "weight_g", "stack_heel_mm", "stack_forefoot_mm", "drop_mm",
  "foam_name", "has_plate", "plate_material", "energy_return_pct",
  "breathability_1to5", "wet_traction", "runrepeat_score", "width_options",
];

export function GET() {
  const data = getShoes().map((s) =>
    Object.fromEntries(FIELDS.map((f) => [f, s[f] ?? ""]))
  );
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
  });
}
