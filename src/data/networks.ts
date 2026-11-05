export type NetworkId = "mtn" | "telecel" | "at";

export type Network = {
  id: NetworkId;
  name: string;
  shortName: string;
  initial: string;
  color: string;
  surface: string;
};

export const networks: Network[] = [
  {
    id: "mtn",
    name: "MTN",
    shortName: "MTN",
    initial: "M",
    color: "#8b6800",
    surface: "#fff6d8",
  },
  {
    id: "telecel",
    name: "Telecel",
    shortName: "Telecel",
    initial: "T",
    color: "#a1275a",
    surface: "#fcecf2",
  },
  {
    id: "at",
    name: "AirtelTigo",
    shortName: "AT",
    initial: "A",
    color: "#2762a0",
    surface: "#edf4fc",
  },
];
