// Auth form validation - same rules as the API, checked before submit (rule "Error Prevention")

export type FormErrors = Record<string, string>;

export function normalizePhone(value: string): string {
  const digits = value.replace(/[\s.\-()]/g, "");
  if (digits.startsWith("+84")) return `0${digits.slice(3)}`;
  if (digits.startsWith("84") && digits.length === 11) return `0${digits.slice(2)}`;
  return digits;
}

export function isValidPhone(value: string): boolean {
  return /^0\d{9}$/.test(normalizePhone(value));
}

export function passwordProblem(value: string): string | null {
  if (value.length < 8) return "At least 8 characters";
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return "Must include a letter and a number";
  if (!/[^A-Za-z0-9]/.test(value)) return "Must include a special character";
  return null;
}

export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export type SignUpForm = {
  full_name: string;
  phone: string;
  email: string;
  password: string;
  confirm_password: string;
  hub_id: string;
  vehicle_plate: string;
  license_no: string;
};

export function validateSignUp(form: SignUpForm): FormErrors {
  const errors: FormErrors = {};
  if (form.full_name.trim().length < 2) errors.full_name = "Please enter your full name";
  if (!isValidPhone(form.phone)) errors.phone = "10 digits starting with 0, or +84";
  if (!isValidEmail(form.email)) errors.email = "Please enter a valid e-mail";
  const problem = passwordProblem(form.password);
  if (problem) errors.password = problem;
  if (form.confirm_password !== form.password) errors.confirm_password = "Must match the password above";
  if (!form.hub_id) errors.hub_id = "Choose the hub you work from";
  if (form.vehicle_plate.trim().length < 4) errors.vehicle_plate = "Please enter your vehicle plate";
  if (form.license_no.trim().length < 6) errors.license_no = "Please enter your licence number";
  return errors;
}
