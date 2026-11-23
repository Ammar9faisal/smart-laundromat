export type MachineType = "WASHER" | "DRYER";

export type MachineStatus =
  | "AVAILABLE"
  | "RESERVED"
  | "IN_USE"
  | "OUT_OF_SERVICE";

export type Machine = {
  id: number;
  type: MachineType;
  capacity: number;
  price: number;
  status: MachineStatus;
  active: boolean;
};

export type BusySlot = {
  start_time: string;
  end_time: string;
};

export type MachineAvailability = {
  machine_id: number;
  from_time: string;
  to_time: string;
  busy: BusySlot[];
};

export type ReservationStatus =
  | "PENDING_PAYMENT"
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "EXPIRED";

export type Reservation = {
  id: number;
  user_id: string;
  machine_id: number;
  start_time: string;
  end_time: string;
  status: ReservationStatus;
  price: number;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  machine: Omit<Machine, "active"> | null;
};

export type PaymentStatus = "PENDING" | "SUCCEEDED" | "FAILED" | "REFUNDED";

export type Payment = {
  id: number;
  reservation_id: number;
  user_id: string;
  amount: number;
  currency: string;
  status: PaymentStatus;
  provider: string;
  provider_ref: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type Profile = {
  id: string;
  email: string;
  full_name: string | null;
  role: "customer" | "admin";
  created_at: string;
};

export type AdminSummary = {
  machines: {
    total: number;
    active: number;
    available: number;
    out_of_service: number;
  };
  reservations_by_status: Partial<Record<ReservationStatus, number>>;
  payments: {
    succeeded: number;
    failed: number;
    refunded: number;
    revenue: number;
  };
};

// Test payment methods accepted by the backend. No real card details are
// ever collected.
export const TEST_PAYMENT_METHODS = [
  { value: "pm_card_visa", label: "Test Visa (succeeds)" },
  { value: "pm_card_mastercard", label: "Test Mastercard (succeeds)" },
  { value: "pm_card_chargeDeclined", label: "Test card: declined" },
  {
    value: "pm_card_chargeDeclinedInsufficientFunds",
    label: "Test card: insufficient funds",
  },
] as const;
