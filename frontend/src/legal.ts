// Pescatourism law per pilot region, shown beside Invest. Every line was read in the cited text on 31 Oct 2026;
// claims we could not read ourselves are left out (listed in CAVEATS.md).
export type Rules = {
  title: string
  sections: { h: string; items: [string, string[]][] }[]  // [text, source ids]
  sources: Record<string, [string, string]>              // id -> [label, url]
}

const GREECE: Rules = {
  title: 'Greece · fishing tourism (αλιευτικός τουρισμός)',
  sections: [
    { h: 'Legal basis', items: [
      ['Created by Law 4070/2012, Arts. 174–184.', ['G1']],
      ['Amended by Law 4179/2013 (Art. 40), Law 5087/2024 (Arts. 15–16) and Law 5121/2024 (Art. 24). Law 4582/2018 (Art. 4) lists it as a form of outdoor tourism.', ['G4', 'G6', 'G7', 'G5']],
      ['Operating rules: Joint Ministerial Decision 414/2354/2015, Gazette B′ 97/20-01-2015.', ['G2']],
    ] },
    { h: 'Vessel', items: [
      ['Professional fishing vessel, overall length up to 15 m.', ['G2', 'G3']],
      ['Fishing licence for gears other than bottom trawl and boat seine.', ['G2']],
      ['Must meet professional tourist-vessel rules (P.D. 917/1979, 918/1979, 270/1988, 399/1980); stability test with fishing gear in use.', ['G2']],
      ['Seaworthiness certificate stating passenger number and voyage range; a passenger area that keeps everyone safe without hindering fishing.', ['G2']],
    ] },
    { h: 'Passengers and activity', items: [
      ['Up to 12 passengers.', ['G2']],
      ['The fisher demonstrates the methods on the vessel’s licence, except bottom trawl and boat seine.', ['G2']],
      ['Tourists may fish only with handline, trolling and vertical line, worked by hand without mechanical aid.', ['G2']],
      ['Full charters and day cruises under Law 4256/2014 are prohibited.', ['G2']],
    ] },
    { h: 'Procedure', items: [
      ['Apply to the Fisheries Service of the regional unit holding the vessel’s file; it works with the local Port Authority.', ['G2']],
      ['Documents: application naming the gear tourists may use, valid professional fishing licence, civil liability insurance (Law 4256/2014, Art. 14).', ['G2']],
      ['Approval entered in the fisheries monitoring system (ΟΣΠΑ) within 5 days of a complete file; notify the Port Authority in writing before starting.', ['G2']],
      ['Official estimate 15 days, €5–100. Filed in person, by post or by email; no online service.', ['G3']],
    ] },
    { h: 'Sanctions', items: [
      ['Law 4070/2012 Art. 182(2–3); Regulation (EC) 1224/2009 with Art. 11 of L.D. 420/1970.', ['G2']],
    ] },
    { h: 'Aquaculture', items: [
      ['Aquaculture support vessels may carry tourists for fishing tourism inside the aquaculture site.', ['G6']],
      ['Enabling clause for fishing tourism in public lagoons, and fishing and diving tourism in aquaculture units.', ['G7']],
      ['JMD 22801/30-12-2024 (Gazette B′ 7315/31-12-2024) sets the conditions for public-lagoon operators and floating or land-based aquaculture units.', ['G8']],
    ] },
    { h: 'Results reported', items: [
      ['Joint project of 18 FLAGs: fishers practising rose from 101 to 157.', ['G9']],
      ['About €500 per trip day; a gillnetter sets about 0.5 km of net on a pescatourism day vs about 5 km fishing.', ['G9']],
    ] },
  ],
  sources: {
    G1: ['Law 4070/2012, Arts. 174–184', 'https://www.taxheaven.gr/law/4070/2012/arthro/174'],
    G2: ['JMD 414/2354/2015 (Gazette B′ 97)', 'https://www.taxheaven.gr/circulars/20271/k-y-a-ariom-414-2354-12-1-2015'],
    G3: ['mitos.gov.gr: fishing tourism approval (updated 22 Sep 2026)', 'https://mitos.gov.gr/index.php/%CE%94%CE%94:%CE%88%CE%B3%CE%BA%CF%81%CE%B9%CF%83%CE%B7_%CE%B4%CE%B9%CE%B5%CE%BD%CE%AD%CF%81%CE%B3%CE%B5%CE%B9%CE%B1%CF%82_%CE%91%CE%BB%CE%B9%CE%B5%CF%85%CF%84%CE%B9%CE%BA%CE%BF%CF%8D_%CE%A4%CE%BF%CF%85%CF%81%CE%B9%CF%83%CE%BC%CE%BF%CF%8D_%CE%B1%CF%80%CF%8C_%CE%B5%CF%80%CE%B1%CE%B3%CE%B3%CE%B5%CE%BB%CE%BC%CE%B1%CF%84%CE%B9%CE%BA%CF%8C_%CE%B1%CE%BB%CE%B9%CE%B5%CF%85%CF%84%CE%B9%CE%BA%CF%8C_%CF%83%CE%BA%CE%AC%CF%86%CE%BF%CF%82'],
    G4: ['Law 4179/2013, Art. 40', 'https://www.taxheaven.gr/law/4179/2013/arthro/40'],
    G5: ['Law 4582/2018, Art. 4', 'https://www.taxheaven.gr/law/4582/2018/arthro/4'],
    G6: ['Law 5087/2024, Arts. 15–16', 'https://www.taxheaven.gr/law/5087/2024/arthro/16'],
    G7: ['Law 5121/2024, Art. 24', 'https://www.taxheaven.gr/law/5121/2024/arthro/24'],
    G8: ['JMD 22801/30-12-2024 (Gazette B′ 7315)', 'https://www.taxheaven.gr/circulars/49321/22801-30-12-2024'],
    G9: ['European Commission: Paving the way for pescatourism', 'https://oceans-and-fisheries.ec.europa.eu/projects/paving-way-pescatourism_en'],
  },
}

const AZORES: Rules = {
  title: 'Azores · pesca-turismo',
  sections: [
    { h: 'Legal basis', items: [
      ['Pescatourism: Regional Legislative Decree (DLR) 36/2008/A, 30 Jul 2008.', ['A1']],
      ['Fishing framework: DLR 29/2010/A, fifth amendment and republication by DLR 10/2026/A (Diário da República 1st series no. 69, 9 Apr 2026). Its Art. 11 leaves pescatourism to its own decree.', ['A2']],
      ['Defined (Art. 6 r) as cultural, leisure and fishing services by a licensed maritime-tourism operator using a regional fishing vessel.', ['A2']],
    ] },
    { h: 'Scope', items: [
      ['Services may include accommodation and food on board, including processing the catch (DLR 36/2008/A Art. 1).', ['A1']],
    ] },
    { h: 'Operator', items: [
      ['Vessel owner or operator, registered seafarer of at least “arrais de pesca local”, working in the region; companies and cooperatives need a manager or board member who qualifies (Art. 4).', ['A1']],
      ['“Arrais de pesca local” is revoked in DLR 29/2010/A (Art. 102); its categories now include “mestre local” (Art. 97).', ['A2']],
    ] },
    { h: 'Vessel', items: [
      ['Only a vessel registered in commercial fishing; vessel characteristics may be set by ordinance (Art. 5).', ['A1']],
      ['Local vessels: up to 9 m, engine up to 100 cv / 75 kW, lower caps by installed power (Art. 57, 2026 wording).', ['A2']],
      ['Coastal vessels: over 9 m to 33 m. Open-deck boats over 9 m and under 14 m may be classed local, up to 30 nm (Art. 58).', ['A2']],
    ] },
    { h: 'Passengers and records', items: [
      ['Most people on board = the vessel’s safety manning certificate; non-crew may not exceed it (Arts. 60, 68).', ['A2']],
      ['Crew = the commercial fishing crew list; clients are not on it (Art. 6).', ['A1']],
      ['Each operation logged with the day, number and names of clients (Art. 6).', ['A1']],
      ['Under-16s only when accompanied or authorised by a parent or guardian (Art. 6).', ['A1']],
    ] },
    { h: 'Operating area', items: [
      ['Local vessels, from the coast of their island: 6 nm open deck, 12 nm open deck with cabin, 30 nm closed deck (Art. 53).', ['A2']],
      ['No fishing near outfalls, ports, small harbours, bathing areas, aquaculture access and natural production zones; distances set by local ordinance (Arts. 24, 26).', ['A2']],
      ['Closed or restricted areas and periods set by ordinance (Arts. 9, 10, 35).', ['A2']],
    ] },
    { h: 'Gear', items: [
      ['Allowed: hand gathering, line, traps, lift nets, purse seine, gillnet (Art. 13).', ['A2']],
      ['Banned: trawl, gillnets deeper than 30 m, drift gillnets, gillnets of more than one panel (Art. 20).', ['A2']],
    ] },
    { h: 'Licences, fees, penalties', items: [
      ['Fishing licences are annual; renewals by 31 Aug with the last 12 months’ gear, landings and sale value (Arts. 42, 44).', ['A2']],
      ['Fee exemption possible for methods consistent with ecosystem sustainability (Art. 47).', ['A2']],
      ['Most serious offences €750–50,000; up to €250,000 for companies; halved for open-deck vessels (Art. 185-A).', ['A2']],
      ['Taking part in an ecolabelled fishery removes 2 penalty points, once every 3 years (Art. 190-F).', ['A2']],
      ['Incentive schemes set by resolution or ordinance (Art. 203).', ['A2']],
    ] },
    { h: 'Ports', items: [
      ['Class D ports: the fisheries department is the port authority. Fishing areas in class A–C ports are “núcleos de pesca” (Art. 202).', ['A2']],
    ] },
  ],
  sources: {
    A1: ['DLR 36/2008/A, Arts. 1–6 (vLex)', 'https://vlex.pt/vid/decreto-legislativo-regional-julho-41383735'],
    A2: ['DLR 10/2026/A with DLR 29/2010/A republished (Diário da República)', 'https://files.diariodarepublica.pt/1s/2026/04/06900/0000900080.pdf'],
  },
}

export const rulesFor = (cc: string, region: string) => cc === 'GR' ? GREECE : region === 'PT20' ? AZORES : undefined
