import { useCallback } from 'react';

interface RefreshTriggerOptions {
  onRefresh: () => Promise<void>;
}

export function useStatusRefreshTrigger({
  onRefresh,
}: RefreshTriggerOptions) {
  const triggerRefresh = useCallback(async () => {
    try {
      console.log('🔄 [useStatusRefreshTrigger] Triggering onRefresh callback');
      await onRefresh();
    } catch (error) {
      console.error('Failed to trigger manual status refresh:', error);
    }
  }, [onRefresh]);

  return {
    triggerRefresh,
  };
}
