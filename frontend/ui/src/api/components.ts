import type { Component, ComponentKind, Result, Version } from '@/types';

import { http } from './http';

export interface CreateComponentInput {
  readonly product_id: string;
  readonly name: string;
  readonly kind: ComponentKind;
}

export interface CreateVersionInput {
  readonly component_id: string;
  readonly version: string;
  readonly prerelease?: string;
}

export function listComponents(
  productId: string,
  signal?: AbortSignal,
): Promise<Result<Component[]>> {
  return http.get<Component[]>(`/products/${productId}/components`, { signal });
}

export function listVersions(
  componentId: string,
  signal?: AbortSignal,
): Promise<Result<Version[]>> {
  return http.get<Version[]>(`/components/${componentId}/versions`, { signal });
}

export function createComponent(input: CreateComponentInput): Promise<Result<Component>> {
  return http.post<Component>('/components', input);
}

export function createVersion(input: CreateVersionInput): Promise<Result<Version>> {
  return http.post<Version>('/versions', input);
}

export function rollbackVersion(versionId: string): Promise<Result<Version>> {
  return http.post<Version>(`/versions/${versionId}/rollback`);
}
