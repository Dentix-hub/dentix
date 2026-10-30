import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getOnboardingStatus,
    dismissOnboarding,
    restoreOnboarding,
    recordTipSeen,
    recordOnboardingEvent,
} from '@/api/onboarding';

export const ONBOARDING_QUERY_KEY = ['onboarding', 'status'];

export function useOnboarding() {
    const queryClient = useQueryClient();

    const {
        data: status,
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ONBOARDING_QUERY_KEY,
        queryFn: getOnboardingStatus,
        staleTime: 60 * 1000,
        refetchOnWindowFocus: true,
    });

    const dismissMutation = useMutation({
        mutationFn: (dismissed = true) => dismissOnboarding(dismissed),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ONBOARDING_QUERY_KEY });
        },
    });

    const restoreMutation = useMutation({
        mutationFn: restoreOnboarding,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ONBOARDING_QUERY_KEY });
        },
    });

    const tipSeenMutation = useMutation({
        mutationFn: (tipKey) => recordTipSeen(tipKey),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ONBOARDING_QUERY_KEY });
        },
    });

    const eventMutation = useMutation({
        mutationFn: (eventKey) => recordOnboardingEvent(eventKey),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ONBOARDING_QUERY_KEY });
        },
    });

    const isTipSeen = (tipKey) => {
        if (!status?.seen_tips) return false;
        return status.seen_tips.includes(tipKey);
    };

    return {
        status,
        isLoading,
        error,
        refetch,
        isTipSeen,
        dismiss: dismissMutation.mutate,
        restore: restoreMutation.mutate,
        markTipSeen: tipSeenMutation.mutate,
        recordEvent: eventMutation.mutate,
    };
}
