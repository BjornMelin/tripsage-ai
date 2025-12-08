/**
 * @fileoverview Hotel chain code mappings from Amadeus to brand names and categories.
 *
 * Amadeus uses 2-character chain codes to identify hotel brands.
 * This mapping enables UI display of brand names and automatic category classification.
 *
 * @see https://amadeus.com/en/resources/amadeus-property-codes
 */

/** Hotel category classification */
export type HotelCategory = "hotel" | "resort" | "boutique" | "apartment" | "villa";

/** Hotel tier classification */
export type HotelTier = "budget" | "midscale" | "upscale" | "luxury";

/** Chain info including brand name and category */
export interface ChainInfo {
  brand: string;
  category: HotelCategory;
  tier: HotelTier;
}

/**
 * Create chain info helper.
 */
function chain(brand: string, category: HotelCategory, tier: HotelTier): ChainInfo {
  return { brand, category, tier };
}

/**
 * Amadeus chain code to brand info mapping.
 * Uses Map for O(1) lookup and to avoid naming convention issues with uppercase keys.
 */
const chainCodeMap: ReadonlyMap<string, ChainInfo> = new Map<string, ChainInfo>([
  // Marriott International
  ["MC", chain("Marriott", "hotel", "upscale")],
  ["SI", chain("Sheraton", "hotel", "upscale")],
  ["WH", chain("W Hotels", "boutique", "luxury")],
  ["WI", chain("Westin", "hotel", "upscale")],
  ["LC", chain("Le Méridien", "boutique", "upscale")],
  ["RC", chain("Ritz-Carlton", "hotel", "luxury")],
  ["XR", chain("St. Regis", "hotel", "luxury")],
  ["AK", chain("Autograph Collection", "boutique", "luxury")],
  ["TX", chain("Tribute Portfolio", "boutique", "upscale")],
  ["CY", chain("Courtyard by Marriott", "hotel", "midscale")],
  ["FN", chain("Fairfield Inn", "hotel", "budget")],
  ["RI", chain("Residence Inn", "apartment", "midscale")],
  ["BR", chain("Renaissance", "hotel", "upscale")],
  ["SH", chain("SpringHill Suites", "hotel", "midscale")],
  ["AR", chain("AC Hotels", "boutique", "upscale")],
  ["AL", chain("Aloft", "boutique", "midscale")],
  ["EL", chain("Element", "hotel", "midscale")],
  ["GE", chain("Gaylord Hotels", "resort", "upscale")],
  ["ED", chain("EDITION", "boutique", "luxury")],
  ["BG", chain("Bulgari", "hotel", "luxury")],
  ["MD", chain("Moxy Hotels", "boutique", "midscale")],
  ["PY", chain("Protea Hotels", "hotel", "midscale")],
  ["DT", chain("Delta Hotels", "hotel", "midscale")],
  ["DE", chain("Design Hotels", "boutique", "luxury")],
  ["OZ", chain("JW Marriott", "hotel", "luxury")],

  // Hilton Worldwide
  ["HI", chain("Hilton", "hotel", "upscale")],
  ["DI", chain("DoubleTree", "hotel", "upscale")],
  ["WA", chain("Waldorf Astoria", "hotel", "luxury")],
  ["RU", chain("Conrad", "hotel", "luxury")],
  ["ES", chain("Embassy Suites", "hotel", "upscale")],
  ["GI", chain("Hilton Garden Inn", "hotel", "midscale")],
  ["HX", chain("Hampton Inn", "hotel", "budget")],
  ["HP", chain("Homewood Suites", "apartment", "midscale")],
  ["HT", chain("Home2 Suites", "apartment", "midscale")],
  ["UP", chain("Curio Collection", "boutique", "luxury")],
  ["OL", chain("LXR Hotels & Resorts", "hotel", "luxury")],
  ["PO", chain("Canopy by Hilton", "boutique", "upscale")],
  ["PE", chain("Signia by Hilton", "hotel", "upscale")],
  ["QQ", chain("Tapestry Collection", "boutique", "upscale")],
  ["TU", chain("Tru by Hilton", "hotel", "budget")],
  ["MO", chain("Motto by Hilton", "boutique", "midscale")],
  ["TP", chain("Tempo by Hilton", "hotel", "midscale")],
  ["GR", chain("Graduate Hotels", "boutique", "upscale")],

  // IHG Hotels & Resorts
  ["IC", chain("InterContinental", "hotel", "luxury")],
  ["CP", chain("Crowne Plaza", "hotel", "upscale")],
  ["HO", chain("Holiday Inn", "hotel", "midscale")],
  ["HE", chain("Holiday Inn Express", "hotel", "budget")],
  ["IN", chain("Hotel Indigo", "boutique", "upscale")],
  ["KI", chain("Kimpton Hotels", "boutique", "luxury")],
  ["EV", chain("Even Hotels", "boutique", "midscale")],
  ["NN", chain("Staybridge Suites", "apartment", "midscale")],
  ["CA", chain("Candlewood Suites", "apartment", "budget")],
  ["VN", chain("voco Hotels", "hotel", "upscale")],
  ["SX", chain("Six Senses", "resort", "luxury")],
  ["RG", chain("Regent Hotels", "hotel", "luxury")],

  // Hyatt Hotels
  ["HY", chain("Hyatt", "hotel", "upscale")],
  ["HR", chain("Hyatt Regency", "hotel", "upscale")],
  ["GH", chain("Grand Hyatt", "hotel", "luxury")],
  ["PH", chain("Park Hyatt", "hotel", "luxury")],
  ["AN", chain("Andaz", "boutique", "luxury")],
  ["UR", chain("Unbound Collection", "boutique", "luxury")],
  ["BH", chain("Hyatt Place", "hotel", "midscale")],
  ["XH", chain("Hyatt House", "apartment", "midscale")],
  ["MI", chain("Miraval", "resort", "luxury")],
  ["AM", chain("Alila", "resort", "luxury")],
  ["TH", chain("Thompson Hotels", "boutique", "luxury")],

  // Accor
  ["SF", chain("Sofitel", "hotel", "luxury")],
  ["PU", chain("Pullman", "hotel", "upscale")],
  ["NG", chain("Novotel", "hotel", "midscale")],
  ["MG", chain("MGallery", "boutique", "upscale")],
  ["IB", chain("Ibis", "hotel", "budget")],
  ["ME", chain("Mercure", "hotel", "midscale")],
  ["FA", chain("Fairmont", "hotel", "luxury")],
  ["RA", chain("Raffles", "hotel", "luxury")],
  ["SW", chain("Swissôtel", "hotel", "upscale")],
  ["SO", chain("SO/ Hotels", "boutique", "luxury")],
  ["BA", chain("Banyan Tree", "resort", "luxury")],
  ["MV", chain("Movenpick", "hotel", "upscale")],
  ["MN", chain("Mantis", "boutique", "luxury")],
  ["HF", chain("25hours Hotels", "boutique", "upscale")],

  // Wyndham Hotels
  ["WY", chain("Wyndham", "hotel", "upscale")],
  ["WG", chain("Wyndham Grand", "hotel", "upscale")],
  ["WT", chain("Wyndham Garden", "hotel", "midscale")],
  ["DQ", chain("Dolce Hotels", "resort", "luxury")],
  ["RW", chain("Ramada", "hotel", "midscale")],
  ["DJ", chain("Days Inn", "hotel", "budget")],
  ["SU", chain("Super 8", "hotel", "budget")],
  ["HJ", chain("Howard Johnson", "hotel", "budget")],
  ["BY", chain("Baymont", "hotel", "budget")],
  ["TL", chain("Travelodge", "hotel", "budget")],
  ["MF", chain("Microtel", "hotel", "budget")],
  ["LA", chain("La Quinta", "hotel", "midscale")],
  ["HW", chain("Hawthorn Suites", "apartment", "midscale")],

  // Best Western
  ["BW", chain("Best Western", "hotel", "midscale")],
  ["WW", chain("WorldHotels", "boutique", "upscale")],
  ["VS", chain("Vīb", "boutique", "midscale")],
  ["GL", chain("GLō", "boutique", "midscale")],
  ["AY", chain("Aiden", "boutique", "midscale")],
  ["SA", chain("SureStay", "hotel", "budget")],

  // Radisson Hotel Group
  ["RD", chain("Radisson", "hotel", "upscale")],
  ["PK", chain("Park Inn", "hotel", "midscale")],
  ["CI", chain("Country Inn & Suites", "hotel", "midscale")],
  ["RP", chain("Radisson Blu", "hotel", "upscale")],
  ["RE", chain("Radisson RED", "boutique", "upscale")],

  // Choice Hotels
  ["QI", chain("Quality Inn", "hotel", "budget")],
  ["SL", chain("Sleep Inn", "hotel", "budget")],
  ["CM", chain("Cambria Hotels", "boutique", "upscale")],
  ["AS", chain("Ascend Collection", "boutique", "upscale")],
  ["CL", chain("Clarion", "hotel", "midscale")],
  ["EI", chain("Econo Lodge", "hotel", "budget")],
  ["RO", chain("Rodeway Inn", "hotel", "budget")],
  ["MS", chain("MainStay Suites", "apartment", "midscale")],
  ["SS", chain("Suburban Extended Stay", "apartment", "budget")],
  ["WO", chain("WoodSpring Suites", "apartment", "budget")],

  // Independent luxury
  ["FS", chain("Four Seasons", "hotel", "luxury")],
  ["PG", chain("Peninsula", "hotel", "luxury")],
  ["LH", chain("Langham", "hotel", "luxury")],
  ["OK", chain("Oetker Collection", "hotel", "luxury")],
  ["RZ", chain("Rosewood", "hotel", "luxury")],
  ["CN", chain("Como Hotels", "resort", "luxury")],
  ["ON", chain("One&Only", "resort", "luxury")],
  ["BE", chain("Belmond", "hotel", "luxury")],
  ["LW", chain("Leading Hotels of the World", "hotel", "luxury")],
  ["PV", chain("Preferred Hotels", "hotel", "luxury")],
  ["RL", chain("Relais & Châteaux", "boutique", "luxury")],
]);

/**
 * Get chain info from Amadeus chain code.
 *
 * @param chainCode - Amadeus 2-character chain code
 * @returns Chain info with brand name and category, or undefined if not found
 */
export function getChainInfo(chainCode: string | undefined): ChainInfo | undefined {
  if (!chainCode) return undefined;
  return chainCodeMap.get(chainCode.toUpperCase());
}

/**
 * Get brand name from Amadeus chain code.
 *
 * @param chainCode - Amadeus 2-character chain code
 * @returns Brand name or undefined if not found
 */
export function getBrandName(chainCode: string | undefined): string | undefined {
  return getChainInfo(chainCode)?.brand;
}

/**
 * Get hotel category from Amadeus chain code.
 * Falls back to "hotel" if chain code is unknown.
 *
 * @param chainCode - Amadeus 2-character chain code
 * @returns Hotel category (hotel, resort, boutique, apartment, villa)
 */
export function getCategoryFromChainCode(chainCode: string | undefined): HotelCategory {
  return getChainInfo(chainCode)?.category ?? "hotel";
}

/**
 * Check if a chain is in the luxury tier.
 *
 * @param chainCode - Amadeus 2-character chain code
 * @returns True if the chain is luxury tier
 */
export function isLuxuryChain(chainCode: string | undefined): boolean {
  return getChainInfo(chainCode)?.tier === "luxury";
}
