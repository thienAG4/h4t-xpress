// Driver hooks - React Query wrappers that keep the home page and shift list in sync

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";
import { cancelRegistration, fetchShiftDays, fetchToday, registerShift, setAvailability } from "./api";

const TODAY_KEY = ["driver", "today"];
const SHIFTS_KEY = ["driver", "shifts"];

export function useDriverToday() {
  return useQuery({ queryKey: TODAY_KEY, queryFn: fetchToday });
}

export function useShiftDays() {
  return useQuery({ queryKey: SHIFTS_KEY, queryFn: () => fetchShiftDays(7) });
}

function useRefreshDriverData() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: TODAY_KEY });
    void queryClient.invalidateQueries({ queryKey: SHIFTS_KEY });
  };
}

export function useRegisterShift() {
  const refresh = useRefreshDriverData();
  return useMutation({
    mutationFn: ({ shiftId, workDate }: { shiftId: string; workDate: string }) =>
      registerShift(shiftId, workDate),
    onSuccess: (registration) => {
      toast.success(`Registered for the ${registration.shift_name.toLowerCase()} shift.`);
      refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCancelRegistration() {
  const refresh = useRefreshDriverData();
  return useMutation({
    mutationFn: cancelRegistration,
    onSuccess: () => {
      toast.success("Shift registration cancelled.");
      refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useSetAvailability() {
  const refresh = useRefreshDriverData();
  return useMutation({
    mutationFn: setAvailability,
    onSuccess: ({ availability }) => {
      toast.success(availability === "ONLINE" ? "You are online and can receive orders." : "You are offline.");
      refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
