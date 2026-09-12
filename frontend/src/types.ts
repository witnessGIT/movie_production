export type StageState = 'pending' | 'running' | 'done' | 'error' | 'skipped'

export interface GPTProfile { id: string; label: string; browser_profile_dir: string; handoff_mode: 'manual_work' | 'manual_chat'; notes: string }
export interface VideoSettings { width: number; height: number; fps: number; target_duration_sec: number; bitrate: string; format: 'mp4' | 'mov' | 'webm'; subtitle_enabled: boolean; aspect_mode: '16:9' | '9:16' | '1:1' | 'custom' }
export interface AppSettings {
  active_gpt_profile_id: string | null
  gpt_profiles: GPTProfile[]
  video: VideoSettings
  models: { tier1_provider: string; tier1_model: string; tier2_provider: string; tier2_model: string; embedding_model: string; strong_model_mode: string }
  max_candidate_clips_per_shot: number
  keep_intermediate_files: boolean
}
export interface Project { id: string; title: string; source_text: string; created_at: string; updated_at: string; asset_count: number }
export interface Asset { id: string; project_id: string; kind: string; media_type: string; label: string; source: string; size_bytes?: number; created_at: string; notes: string }
export interface Stage { id: string; label: string; state: StageState; progress: number; detail: string; artifact?: string }
export interface TimelineSegment { id: number; start: number; end: number; label: string; track: string }
export interface Job { id: string; project_id: string; state: 'queued'|'running'|'done'|'error'; stages: Stage[]; logs: string[]; timeline: TimelineSegment[] }
export interface Capability { id: string; label: string; available: boolean; detail: string; tier: string }
