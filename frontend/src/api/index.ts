import { mockApi } from './mock';
import { realApi } from './real';
import type { Api } from './types';

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

export const api: Api = USE_MOCKS ? mockApi : realApi;
