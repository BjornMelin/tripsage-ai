// MANUAL PATCH 2025-11-29: trips.notes removed; trips.tags text[]|null added.
// After Supabase DB migration, regenerate via `supabase gen types typescript --local` and remove this notice.
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  auth: {
    Tables: {
      audit_log_entries: {
        Row: {
          created_at: string | null;
          id: string;
          instance_id: string | null;
          ip_address: string;
          payload: Json | null;
        };
        Insert: {
          created_at?: string | null;
          id: string;
          instance_id?: string | null;
          ip_address?: string;
          payload?: Json | null;
        };
        Update: {
          created_at?: string | null;
          id?: string;
          instance_id?: string | null;
          ip_address?: string;
          payload?: Json | null;
        };
        Relationships: [];
      };
      flow_state: {
        Row: {
          auth_code: string;
          auth_code_issued_at: string | null;
          authentication_method: string;
          code_challenge: string;
          code_challenge_method: Database["auth"]["Enums"]["code_challenge_method"];
          created_at: string | null;
          id: string;
          provider_access_token: string | null;
          provider_refresh_token: string | null;
          provider_type: string;
          updated_at: string | null;
          user_id: string | null;
        };
        Insert: {
          auth_code: string;
          auth_code_issued_at?: string | null;
          authentication_method: string;
          code_challenge: string;
          code_challenge_method: Database["auth"]["Enums"]["code_challenge_method"];
          created_at?: string | null;
          id: string;
          provider_access_token?: string | null;
          provider_refresh_token?: string | null;
          provider_type: string;
          updated_at?: string | null;
          user_id?: string | null;
        };
        Update: {
          auth_code?: string;
          auth_code_issued_at?: string | null;
          authentication_method?: string;
          code_challenge?: string;
          code_challenge_method?: Database["auth"]["Enums"]["code_challenge_method"];
          created_at?: string | null;
          id?: string;
          provider_access_token?: string | null;
          provider_refresh_token?: string | null;
          provider_type?: string;
          updated_at?: string | null;
          user_id?: string | null;
        };
        Relationships: [];
      };
      identities: {
        Row: {
          created_at: string | null;
          email: string | null;
          id: string;
          identity_data: Json;
          last_sign_in_at: string | null;
          provider: string;
          provider_id: string;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          created_at?: string | null;
          email?: string | null;
          id?: string;
          identity_data: Json;
          last_sign_in_at?: string | null;
          provider: string;
          provider_id: string;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          created_at?: string | null;
          email?: string | null;
          id?: string;
          identity_data?: Json;
          last_sign_in_at?: string | null;
          provider?: string;
          provider_id?: string;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "identities_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
        ];
      };
      instances: {
        Row: {
          created_at: string | null;
          id: string;
          raw_base_config: string | null;
          updated_at: string | null;
          uuid: string | null;
        };
        Insert: {
          created_at?: string | null;
          id: string;
          raw_base_config?: string | null;
          updated_at?: string | null;
          uuid?: string | null;
        };
        Update: {
          created_at?: string | null;
          id?: string;
          raw_base_config?: string | null;
          updated_at?: string | null;
          uuid?: string | null;
        };
        Relationships: [];
      };
      mfa_amr_claims: {
        Row: {
          authentication_method: string;
          created_at: string;
          id: string;
          session_id: string;
          updated_at: string;
        };
        Insert: {
          authentication_method: string;
          created_at: string;
          id: string;
          session_id: string;
          updated_at: string;
        };
        Update: {
          authentication_method?: string;
          created_at?: string;
          id?: string;
          session_id?: string;
          updated_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "mfa_amr_claims_session_id_fkey";
            columns: ["session_id"];
            isOneToOne: false;
            referencedRelation: "sessions";
            referencedColumns: ["id"];
          },
        ];
      };
      mfa_challenges: {
        Row: {
          created_at: string;
          factor_id: string;
          id: string;
          ip_address: unknown;
          otp_code: string | null;
          verified_at: string | null;
          web_authn_session_data: Json | null;
        };
        Insert: {
          created_at: string;
          factor_id: string;
          id: string;
          ip_address: unknown;
          otp_code?: string | null;
          verified_at?: string | null;
          web_authn_session_data?: Json | null;
        };
        Update: {
          created_at?: string;
          factor_id?: string;
          id?: string;
          ip_address?: unknown;
          otp_code?: string | null;
          verified_at?: string | null;
          web_authn_session_data?: Json | null;
        };
        Relationships: [
          {
            foreignKeyName: "mfa_challenges_auth_factor_id_fkey";
            columns: ["factor_id"];
            isOneToOne: false;
            referencedRelation: "mfa_factors";
            referencedColumns: ["id"];
          },
        ];
      };
      mfa_factors: {
        Row: {
          created_at: string;
          factor_type: Database["auth"]["Enums"]["factor_type"];
          friendly_name: string | null;
          id: string;
          last_challenged_at: string | null;
          phone: string | null;
          secret: string | null;
          status: Database["auth"]["Enums"]["factor_status"];
          updated_at: string;
          user_id: string;
          web_authn_aaguid: string | null;
          web_authn_credential: Json | null;
        };
        Insert: {
          created_at: string;
          factor_type: Database["auth"]["Enums"]["factor_type"];
          friendly_name?: string | null;
          id: string;
          last_challenged_at?: string | null;
          phone?: string | null;
          secret?: string | null;
          status: Database["auth"]["Enums"]["factor_status"];
          updated_at: string;
          user_id: string;
          web_authn_aaguid?: string | null;
          web_authn_credential?: Json | null;
        };
        Update: {
          created_at?: string;
          factor_type?: Database["auth"]["Enums"]["factor_type"];
          friendly_name?: string | null;
          id?: string;
          last_challenged_at?: string | null;
          phone?: string | null;
          secret?: string | null;
          status?: Database["auth"]["Enums"]["factor_status"];
          updated_at?: string;
          user_id?: string;
          web_authn_aaguid?: string | null;
          web_authn_credential?: Json | null;
        };
        Relationships: [
          {
            foreignKeyName: "mfa_factors_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
        ];
      };
      oauth_authorizations: {
        Row: {
          approved_at: string | null;
          authorization_code: string | null;
          authorization_id: string;
          client_id: string;
          code_challenge: string | null;
          code_challenge_method:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null;
          created_at: string;
          expires_at: string;
          id: string;
          redirect_uri: string;
          resource: string | null;
          response_type: Database["auth"]["Enums"]["oauth_response_type"];
          scope: string;
          state: string | null;
          status: Database["auth"]["Enums"]["oauth_authorization_status"];
          user_id: string | null;
        };
        Insert: {
          approved_at?: string | null;
          authorization_code?: string | null;
          authorization_id: string;
          client_id: string;
          code_challenge?: string | null;
          code_challenge_method?:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null;
          created_at?: string;
          expires_at?: string;
          id: string;
          redirect_uri: string;
          resource?: string | null;
          response_type?: Database["auth"]["Enums"]["oauth_response_type"];
          scope: string;
          state?: string | null;
          status?: Database["auth"]["Enums"]["oauth_authorization_status"];
          user_id?: string | null;
        };
        Update: {
          approved_at?: string | null;
          authorization_code?: string | null;
          authorization_id?: string;
          client_id?: string;
          code_challenge?: string | null;
          code_challenge_method?:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null;
          created_at?: string;
          expires_at?: string;
          id?: string;
          redirect_uri?: string;
          resource?: string | null;
          response_type?: Database["auth"]["Enums"]["oauth_response_type"];
          scope?: string;
          state?: string | null;
          status?: Database["auth"]["Enums"]["oauth_authorization_status"];
          user_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "oauth_authorizations_client_id_fkey";
            columns: ["client_id"];
            isOneToOne: false;
            referencedRelation: "oauth_clients";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "oauth_authorizations_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
        ];
      };
      oauth_clients: {
        Row: {
          client_name: string | null;
          client_secret_hash: string | null;
          client_type: Database["auth"]["Enums"]["oauth_client_type"];
          client_uri: string | null;
          created_at: string;
          deleted_at: string | null;
          grant_types: string;
          id: string;
          logo_uri: string | null;
          redirect_uris: string;
          registration_type: Database["auth"]["Enums"]["oauth_registration_type"];
          updated_at: string;
        };
        Insert: {
          client_name?: string | null;
          client_secret_hash?: string | null;
          client_type?: Database["auth"]["Enums"]["oauth_client_type"];
          client_uri?: string | null;
          created_at?: string;
          deleted_at?: string | null;
          grant_types: string;
          id: string;
          logo_uri?: string | null;
          redirect_uris: string;
          registration_type: Database["auth"]["Enums"]["oauth_registration_type"];
          updated_at?: string;
        };
        Update: {
          client_name?: string | null;
          client_secret_hash?: string | null;
          client_type?: Database["auth"]["Enums"]["oauth_client_type"];
          client_uri?: string | null;
          created_at?: string;
          deleted_at?: string | null;
          grant_types?: string;
          id?: string;
          logo_uri?: string | null;
          redirect_uris?: string;
          registration_type?: Database["auth"]["Enums"]["oauth_registration_type"];
          updated_at?: string;
        };
        Relationships: [];
      };
      oauth_consents: {
        Row: {
          client_id: string;
          granted_at: string;
          id: string;
          revoked_at: string | null;
          scopes: string;
          user_id: string;
        };
        Insert: {
          client_id: string;
          granted_at?: string;
          id: string;
          revoked_at?: string | null;
          scopes: string;
          user_id: string;
        };
        Update: {
          client_id?: string;
          granted_at?: string;
          id?: string;
          revoked_at?: string | null;
          scopes?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "oauth_consents_client_id_fkey";
            columns: ["client_id"];
            isOneToOne: false;
            referencedRelation: "oauth_clients";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "oauth_consents_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
        ];
      };
      one_time_tokens: {
        Row: {
          created_at: string;
          id: string;
          relates_to: string;
          token_hash: string;
          token_type: Database["auth"]["Enums"]["one_time_token_type"];
          updated_at: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          id: string;
          relates_to: string;
          token_hash: string;
          token_type: Database["auth"]["Enums"]["one_time_token_type"];
          updated_at?: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          id?: string;
          relates_to?: string;
          token_hash?: string;
          token_type?: Database["auth"]["Enums"]["one_time_token_type"];
          updated_at?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "one_time_tokens_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
        ];
      };
      refresh_tokens: {
        Row: {
          created_at: string | null;
          id: number;
          instance_id: string | null;
          parent: string | null;
          revoked: boolean | null;
          session_id: string | null;
          token: string | null;
          updated_at: string | null;
          user_id: string | null;
        };
        Insert: {
          created_at?: string | null;
          id?: number;
          instance_id?: string | null;
          parent?: string | null;
          revoked?: boolean | null;
          session_id?: string | null;
          token?: string | null;
          updated_at?: string | null;
          user_id?: string | null;
        };
        Update: {
          created_at?: string | null;
          id?: number;
          instance_id?: string | null;
          parent?: string | null;
          revoked?: boolean | null;
          session_id?: string | null;
          token?: string | null;
          updated_at?: string | null;
          user_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "refresh_tokens_session_id_fkey";
            columns: ["session_id"];
            isOneToOne: false;
            referencedRelation: "sessions";
            referencedColumns: ["id"];
          },
        ];
      };
      saml_providers: {
        Row: {
          attribute_mapping: Json | null;
          created_at: string | null;
          entity_id: string;
          id: string;
          metadata_url: string | null;
          metadata_xml: string;
          name_id_format: string | null;
          sso_provider_id: string;
          updated_at: string | null;
        };
        Insert: {
          attribute_mapping?: Json | null;
          created_at?: string | null;
          entity_id: string;
          id: string;
          metadata_url?: string | null;
          metadata_xml: string;
          name_id_format?: string | null;
          sso_provider_id: string;
          updated_at?: string | null;
        };
        Update: {
          attribute_mapping?: Json | null;
          created_at?: string | null;
          entity_id?: string;
          id?: string;
          metadata_url?: string | null;
          metadata_xml?: string;
          name_id_format?: string | null;
          sso_provider_id?: string;
          updated_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "saml_providers_sso_provider_id_fkey";
            columns: ["sso_provider_id"];
            isOneToOne: false;
            referencedRelation: "sso_providers";
            referencedColumns: ["id"];
          },
        ];
      };
      saml_relay_states: {
        Row: {
          created_at: string | null;
          flow_state_id: string | null;
          for_email: string | null;
          id: string;
          redirect_to: string | null;
          request_id: string;
          sso_provider_id: string;
          updated_at: string | null;
        };
        Insert: {
          created_at?: string | null;
          flow_state_id?: string | null;
          for_email?: string | null;
          id: string;
          redirect_to?: string | null;
          request_id: string;
          sso_provider_id: string;
          updated_at?: string | null;
        };
        Update: {
          created_at?: string | null;
          flow_state_id?: string | null;
          for_email?: string | null;
          id?: string;
          redirect_to?: string | null;
          request_id?: string;
          sso_provider_id?: string;
          updated_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "saml_relay_states_flow_state_id_fkey";
            columns: ["flow_state_id"];
            isOneToOne: false;
            referencedRelation: "flow_state";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "saml_relay_states_sso_provider_id_fkey";
            columns: ["sso_provider_id"];
            isOneToOne: false;
            referencedRelation: "sso_providers";
            referencedColumns: ["id"];
          },
        ];
      };
      schema_migrations: {
        Row: {
          version: string;
        };
        Insert: {
          version: string;
        };
        Update: {
          version?: string;
        };
        Relationships: [];
      };
      sessions: {
        Row: {
          aal: Database["auth"]["Enums"]["aal_level"] | null;
          created_at: string | null;
          factor_id: string | null;
          id: string;
          ip: unknown;
          not_after: string | null;
          oauth_client_id: string | null;
          refreshed_at: string | null;
          tag: string | null;
          updated_at: string | null;
          user_agent: string | null;
          user_id: string;
        };
        Insert: {
          aal?: Database["auth"]["Enums"]["aal_level"] | null;
          created_at?: string | null;
          factor_id?: string | null;
          id: string;
          ip?: unknown;
          not_after?: string | null;
          oauth_client_id?: string | null;
          refreshed_at?: string | null;
          tag?: string | null;
          updated_at?: string | null;
          user_agent?: string | null;
          user_id: string;
        };
        Update: {
          aal?: Database["auth"]["Enums"]["aal_level"] | null;
          created_at?: string | null;
          factor_id?: string | null;
          id?: string;
          ip?: unknown;
          not_after?: string | null;
          oauth_client_id?: string | null;
          refreshed_at?: string | null;
          tag?: string | null;
          updated_at?: string | null;
          user_agent?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "sessions_oauth_client_id_fkey";
            columns: ["oauth_client_id"];
            isOneToOne: false;
            referencedRelation: "oauth_clients";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "sessions_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          },
        ];
      };
      sso_domains: {
        Row: {
          created_at: string | null;
          domain: string;
          id: string;
          sso_provider_id: string;
          updated_at: string | null;
        };
        Insert: {
          created_at?: string | null;
          domain: string;
          id: string;
          sso_provider_id: string;
          updated_at?: string | null;
        };
        Update: {
          created_at?: string | null;
          domain?: string;
          id?: string;
          sso_provider_id?: string;
          updated_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "sso_domains_sso_provider_id_fkey";
            columns: ["sso_provider_id"];
            isOneToOne: false;
            referencedRelation: "sso_providers";
            referencedColumns: ["id"];
          },
        ];
      };
      sso_providers: {
        Row: {
          created_at: string | null;
          disabled: boolean | null;
          id: string;
          resource_id: string | null;
          updated_at: string | null;
        };
        Insert: {
          created_at?: string | null;
          disabled?: boolean | null;
          id: string;
          resource_id?: string | null;
          updated_at?: string | null;
        };
        Update: {
          created_at?: string | null;
          disabled?: boolean | null;
          id?: string;
          resource_id?: string | null;
          updated_at?: string | null;
        };
        Relationships: [];
      };
      users: {
        Row: {
          aud: string | null;
          banned_until: string | null;
          confirmation_sent_at: string | null;
          confirmation_token: string | null;
          confirmed_at: string | null;
          created_at: string | null;
          deleted_at: string | null;
          email: string | null;
          email_change: string | null;
          email_change_confirm_status: number | null;
          email_change_sent_at: string | null;
          email_change_token_current: string | null;
          email_change_token_new: string | null;
          email_confirmed_at: string | null;
          encrypted_password: string | null;
          id: string;
          instance_id: string | null;
          invited_at: string | null;
          is_anonymous: boolean;
          is_sso_user: boolean;
          is_super_admin: boolean | null;
          last_sign_in_at: string | null;
          phone: string | null;
          phone_change: string | null;
          phone_change_sent_at: string | null;
          phone_change_token: string | null;
          phone_confirmed_at: string | null;
          raw_app_meta_data: Json | null;
          raw_user_meta_data: Json | null;
          reauthentication_sent_at: string | null;
          reauthentication_token: string | null;
          recovery_sent_at: string | null;
          recovery_token: string | null;
          role: string | null;
          updated_at: string | null;
        };
        Insert: {
          aud?: string | null;
          banned_until?: string | null;
          confirmation_sent_at?: string | null;
          confirmation_token?: string | null;
          confirmed_at?: string | null;
          created_at?: string | null;
          deleted_at?: string | null;
          email?: string | null;
          email_change?: string | null;
          email_change_confirm_status?: number | null;
          email_change_sent_at?: string | null;
          email_change_token_current?: string | null;
          email_change_token_new?: string | null;
          email_confirmed_at?: string | null;
          encrypted_password?: string | null;
          id: string;
          instance_id?: string | null;
          invited_at?: string | null;
          is_anonymous?: boolean;
          is_sso_user?: boolean;
          is_super_admin?: boolean | null;
          last_sign_in_at?: string | null;
          phone?: string | null;
          phone_change?: string | null;
          phone_change_sent_at?: string | null;
          phone_change_token?: string | null;
          phone_confirmed_at?: string | null;
          raw_app_meta_data?: Json | null;
          raw_user_meta_data?: Json | null;
          reauthentication_sent_at?: string | null;
          reauthentication_token?: string | null;
          recovery_sent_at?: string | null;
          recovery_token?: string | null;
          role?: string | null;
          updated_at?: string | null;
        };
        Update: {
          aud?: string | null;
          banned_until?: string | null;
          confirmation_sent_at?: string | null;
          confirmation_token?: string | null;
          confirmed_at?: string | null;
          created_at?: string | null;
          deleted_at?: string | null;
          email?: string | null;
          email_change?: string | null;
          email_change_confirm_status?: number | null;
          email_change_sent_at?: string | null;
          email_change_token_current?: string | null;
          email_change_token_new?: string | null;
          email_confirmed_at?: string | null;
          encrypted_password?: string | null;
          id?: string;
          instance_id?: string | null;
          invited_at?: string | null;
          is_anonymous?: boolean;
          is_sso_user?: boolean;
          is_super_admin?: boolean | null;
          last_sign_in_at?: string | null;
          phone?: string | null;
          phone_change?: string | null;
          phone_change_sent_at?: string | null;
          phone_change_token?: string | null;
          phone_confirmed_at?: string | null;
          raw_app_meta_data?: Json | null;
          raw_user_meta_data?: Json | null;
          reauthentication_sent_at?: string | null;
          reauthentication_token?: string | null;
          recovery_sent_at?: string | null;
          recovery_token?: string | null;
          role?: string | null;
          updated_at?: string | null;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      email: { Args: never; Returns: string };
      jwt: { Args: never; Returns: Json };
      role: { Args: never; Returns: string };
      uid: { Args: never; Returns: string };
    };
    Enums: {
      aal_level: "aal1" | "aal2" | "aal3";
      code_challenge_method: "s256" | "plain";
      factor_status: "unverified" | "verified";
      factor_type: "totp" | "webauthn" | "phone";
      oauth_authorization_status: "pending" | "approved" | "denied" | "expired";
      oauth_client_type: "public" | "confidential";
      oauth_registration_type: "dynamic" | "manual";
      oauth_response_type: "code";
      one_time_token_type:
        | "confirmation_token"
        | "reauthentication_token"
        | "recovery_token"
        | "email_change_token_new"
        | "email_change_token_current"
        | "phone_change_token";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
  memories: {
    Tables: {
      sessions: {
        Row: {
          created_at: string;
          id: string;
          last_synced_at: string | null;
          metadata: Json;
          title: string;
          updated_at: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          id?: string;
          last_synced_at?: string | null;
          metadata?: Json;
          title: string;
          updated_at?: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          id?: string;
          last_synced_at?: string | null;
          metadata?: Json;
          title?: string;
          updated_at?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      turn_embeddings: {
        Row: {
          created_at: string;
          embedding: string;
          model: string;
          turn_id: string;
        };
        Insert: {
          created_at?: string;
          embedding: string;
          model: string;
          turn_id: string;
        };
        Update: {
          created_at?: string;
          embedding?: string;
          model?: string;
          turn_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "turn_embeddings_turn_id_fkey";
            columns: ["turn_id"];
            isOneToOne: true;
            referencedRelation: "turns";
            referencedColumns: ["id"];
          },
        ];
      };
      turns: {
        Row: {
          attachments: Json;
          content: Json;
          created_at: string;
          id: string;
          pii_scrubbed: boolean;
          role: string;
          session_id: string;
          tool_calls: Json;
          tool_results: Json;
          user_id: string;
        };
        Insert: {
          attachments?: Json;
          content: Json;
          created_at?: string;
          id?: string;
          pii_scrubbed?: boolean;
          role: string;
          session_id: string;
          tool_calls?: Json;
          tool_results?: Json;
          user_id: string;
        };
        Update: {
          attachments?: Json;
          content?: Json;
          created_at?: string;
          id?: string;
          pii_scrubbed?: boolean;
          role?: string;
          session_id?: string;
          tool_calls?: Json;
          tool_results?: Json;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "turns_session_id_fkey";
            columns: ["session_id"];
            isOneToOne: false;
            referencedRelation: "sessions";
            referencedColumns: ["id"];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
  public: {
    Tables: {
      accommodation_embeddings: {
        Row: {
          amenities: string | null;
          created_at: string | null;
          description: string | null;
          embedding: string | null;
          id: string;
          name: string | null;
          source: string;
          updated_at: string | null;
        };
        Insert: {
          amenities?: string | null;
          created_at?: string | null;
          description?: string | null;
          embedding?: string | null;
          id: string;
          name?: string | null;
          source: string;
          updated_at?: string | null;
        };
        Update: {
          amenities?: string | null;
          created_at?: string | null;
          description?: string | null;
          embedding?: string | null;
          id?: string;
          name?: string | null;
          source?: string;
          updated_at?: string | null;
        };
        Relationships: [];
      };
      accommodations: {
        Row: {
          address: string | null;
          amenities: string[] | null;
          booking_status: string;
          check_in_date: string;
          check_out_date: string;
          created_at: string | null;
          currency: string;
          external_id: string | null;
          id: number;
          metadata: Json | null;
          name: string;
          price_per_night: number;
          rating: number | null;
          room_type: string | null;
          total_price: number;
          trip_id: number;
          updated_at: string | null;
        };
        Insert: {
          address?: string | null;
          amenities?: string[] | null;
          booking_status?: string;
          check_in_date: string;
          check_out_date: string;
          created_at?: string | null;
          currency?: string;
          external_id?: string | null;
          id?: never;
          metadata?: Json | null;
          name: string;
          price_per_night: number;
          rating?: number | null;
          room_type?: string | null;
          total_price: number;
          trip_id: number;
          updated_at?: string | null;
        };
        Update: {
          address?: string | null;
          amenities?: string[] | null;
          booking_status?: string;
          check_in_date?: string;
          check_out_date?: string;
          created_at?: string | null;
          currency?: string;
          external_id?: string | null;
          id?: never;
          metadata?: Json | null;
          name?: string;
          price_per_night?: number;
          rating?: number | null;
          room_type?: string | null;
          total_price?: number;
          trip_id?: number;
          updated_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "accommodations_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      agent_config: {
        Row: {
          agent_type: string;
          config: Json;
          created_at: string;
          id: string;
          scope: string;
          updated_at: string;
          version_id: string;
        };
        Insert: {
          agent_type: string;
          config: Json;
          created_at?: string;
          id?: string;
          scope?: string;
          updated_at?: string;
          version_id: string;
        };
        Update: {
          agent_type?: string;
          config?: Json;
          created_at?: string;
          id?: string;
          scope?: string;
          updated_at?: string;
          version_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "agent_config_version_id_fkey";
            columns: ["version_id"];
            isOneToOne: false;
            referencedRelation: "agent_config_versions";
            referencedColumns: ["id"];
          },
        ];
      };
      agent_config_versions: {
        Row: {
          agent_type: string;
          config: Json;
          created_at: string;
          created_by: string | null;
          id: string;
          scope: string;
          summary: string | null;
        };
        Insert: {
          agent_type: string;
          config: Json;
          created_at?: string;
          created_by?: string | null;
          id?: string;
          scope?: string;
          summary?: string | null;
        };
        Update: {
          agent_type?: string;
          config?: Json;
          created_at?: string;
          created_by?: string | null;
          id?: string;
          scope?: string;
          summary?: string | null;
        };
        Relationships: [];
      };
      api_gateway_configs: {
        Row: {
          base_url: string | null;
          user_id: string;
        };
        Insert: {
          base_url?: string | null;
          user_id: string;
        };
        Update: {
          base_url?: string | null;
          user_id?: string;
        };
        Relationships: [];
      };
      api_keys: {
        Row: {
          created_at: string | null;
          id: number;
          last_used: string | null;
          service: string;
          user_id: string;
          vault_secret_name: string;
        };
        Insert: {
          created_at?: string | null;
          id?: never;
          last_used?: string | null;
          service: string;
          user_id: string;
          vault_secret_name: string;
        };
        Update: {
          created_at?: string | null;
          id?: never;
          last_used?: string | null;
          service?: string;
          user_id?: string;
          vault_secret_name?: string;
        };
        Relationships: [];
      };
      bookings: {
        Row: {
          booking_token: string | null;
          checkin: string;
          checkout: string;
          created_at: string | null;
          guest_email: string;
          guest_name: string;
          guest_phone: string | null;
          guests: number;
          id: string;
          property_id: string;
          provider_booking_id: string;
          special_requests: string | null;
          status: string;
          stripe_payment_intent_id: string | null;
          trip_id: number | null;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          booking_token?: string | null;
          checkin: string;
          checkout: string;
          created_at?: string | null;
          guest_email: string;
          guest_name: string;
          guest_phone?: string | null;
          guests: number;
          id: string;
          property_id: string;
          provider_booking_id: string;
          special_requests?: string | null;
          status: string;
          stripe_payment_intent_id?: string | null;
          trip_id?: number | null;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          booking_token?: string | null;
          checkin?: string;
          checkout?: string;
          created_at?: string | null;
          guest_email?: string;
          guest_name?: string;
          guest_phone?: string | null;
          guests?: number;
          id?: string;
          property_id?: string;
          provider_booking_id?: string;
          special_requests?: string | null;
          status?: string;
          stripe_payment_intent_id?: string | null;
          trip_id?: number | null;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "bookings_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      chat_messages: {
        Row: {
          content: string;
          created_at: string | null;
          id: number;
          metadata: Json | null;
          role: string;
          session_id: string;
          user_id: string;
        };
        Insert: {
          content: string;
          created_at?: string | null;
          id?: never;
          metadata?: Json | null;
          role: string;
          session_id: string;
          user_id: string;
        };
        Update: {
          content?: string;
          created_at?: string | null;
          id?: never;
          metadata?: Json | null;
          role?: string;
          session_id?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "chat_messages_session_id_fkey";
            columns: ["session_id"];
            isOneToOne: false;
            referencedRelation: "chat_sessions";
            referencedColumns: ["id"];
          },
        ];
      };
      chat_sessions: {
        Row: {
          created_at: string | null;
          id: string;
          metadata: Json | null;
          trip_id: number | null;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          created_at?: string | null;
          id?: string;
          metadata?: Json | null;
          trip_id?: number | null;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          created_at?: string | null;
          id?: string;
          metadata?: Json | null;
          trip_id?: number | null;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "chat_sessions_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      chat_tool_calls: {
        Row: {
          arguments: Json;
          completed_at: string | null;
          created_at: string | null;
          error_message: string | null;
          id: number;
          message_id: number;
          result: Json | null;
          status: string;
          tool_id: string;
          tool_name: string;
        };
        Insert: {
          arguments?: Json;
          completed_at?: string | null;
          created_at?: string | null;
          error_message?: string | null;
          id?: never;
          message_id: number;
          result?: Json | null;
          status?: string;
          tool_id: string;
          tool_name: string;
        };
        Update: {
          arguments?: Json;
          completed_at?: string | null;
          created_at?: string | null;
          error_message?: string | null;
          id?: never;
          message_id?: number;
          result?: Json | null;
          status?: string;
          tool_id?: string;
          tool_name?: string;
        };
        Relationships: [
          {
            foreignKeyName: "chat_tool_calls_message_id_fkey";
            columns: ["message_id"];
            isOneToOne: false;
            referencedRelation: "chat_messages";
            referencedColumns: ["id"];
          },
        ];
      };
      file_attachments: {
        Row: {
          bucket_name: string;
          chat_message_id: number | null;
          created_at: string | null;
          file_path: string;
          file_size: number;
          filename: string;
          id: string;
          metadata: Json;
          mime_type: string;
          original_filename: string;
          trip_id: number | null;
          updated_at: string | null;
          upload_status: string;
          user_id: string;
          virus_scan_result: Json;
          virus_scan_status: string;
        };
        Insert: {
          bucket_name?: string;
          chat_message_id?: number | null;
          created_at?: string | null;
          file_path: string;
          file_size: number;
          filename: string;
          id?: string;
          metadata?: Json;
          mime_type: string;
          original_filename: string;
          trip_id?: number | null;
          updated_at?: string | null;
          upload_status?: string;
          user_id: string;
          virus_scan_result?: Json;
          virus_scan_status?: string;
        };
        Update: {
          bucket_name?: string;
          chat_message_id?: number | null;
          created_at?: string | null;
          file_path?: string;
          file_size?: number;
          filename?: string;
          id?: string;
          metadata?: Json;
          mime_type?: string;
          original_filename?: string;
          trip_id?: number | null;
          updated_at?: string | null;
          upload_status?: string;
          user_id?: string;
          virus_scan_result?: Json;
          virus_scan_status?: string;
        };
        Relationships: [
          {
            foreignKeyName: "file_attachments_chat_message_id_fkey";
            columns: ["chat_message_id"];
            isOneToOne: false;
            referencedRelation: "chat_messages";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "file_attachments_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      file_processing_queue: {
        Row: {
          attempts: number;
          completed_at: string | null;
          created_at: string | null;
          error_message: string | null;
          file_attachment_id: string;
          id: number;
          max_attempts: number;
          metadata: Json | null;
          operation: string;
          priority: number;
          scheduled_at: string | null;
          started_at: string | null;
          status: string;
          updated_at: string | null;
        };
        Insert: {
          attempts?: number;
          completed_at?: string | null;
          created_at?: string | null;
          error_message?: string | null;
          file_attachment_id: string;
          id?: never;
          max_attempts?: number;
          metadata?: Json | null;
          operation: string;
          priority?: number;
          scheduled_at?: string | null;
          started_at?: string | null;
          status?: string;
          updated_at?: string | null;
        };
        Update: {
          attempts?: number;
          completed_at?: string | null;
          created_at?: string | null;
          error_message?: string | null;
          file_attachment_id?: string;
          id?: never;
          max_attempts?: number;
          metadata?: Json | null;
          operation?: string;
          priority?: number;
          scheduled_at?: string | null;
          started_at?: string | null;
          status?: string;
          updated_at?: string | null;
        };
        Relationships: [];
      };
      file_versions: {
        Row: {
          change_description: string | null;
          checksum: string;
          created_at: string | null;
          created_by: string;
          file_attachment_id: string;
          file_path: string;
          file_size: number;
          id: number;
          is_current: boolean;
          version_number: number;
        };
        Insert: {
          change_description?: string | null;
          checksum: string;
          created_at?: string | null;
          created_by: string;
          file_attachment_id: string;
          file_path: string;
          file_size: number;
          id?: never;
          is_current?: boolean;
          version_number: number;
        };
        Update: {
          change_description?: string | null;
          checksum?: string;
          created_at?: string | null;
          created_by?: string;
          file_attachment_id?: string;
          file_path?: string;
          file_size?: number;
          id?: never;
          is_current?: boolean;
          version_number?: number;
        };
        Relationships: [];
      };
      flights: {
        Row: {
          airline: string | null;
          booking_status: string;
          created_at: string | null;
          currency: string;
          departure_date: string;
          destination: string;
          external_id: string | null;
          flight_class: string;
          flight_number: string | null;
          id: number;
          metadata: Json | null;
          origin: string;
          price: number;
          return_date: string | null;
          trip_id: number;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          airline?: string | null;
          booking_status?: string;
          created_at?: string | null;
          currency?: string;
          departure_date: string;
          destination: string;
          external_id?: string | null;
          flight_class?: string;
          flight_number?: string | null;
          id?: never;
          metadata?: Json | null;
          origin: string;
          price: number;
          return_date?: string | null;
          trip_id: number;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          airline?: string | null;
          booking_status?: string;
          created_at?: string | null;
          currency?: string;
          departure_date?: string;
          destination?: string;
          external_id?: string | null;
          flight_class?: string;
          flight_number?: string | null;
          id?: never;
          metadata?: Json | null;
          origin?: string;
          price?: number;
          return_date?: string | null;
          trip_id?: number;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "flights_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      gateway_user_keys: {
        Row: {
          created_at: string | null;
          encrypted_key: string;
          id: number;
          provider: string;
          user_id: string;
        };
        Insert: {
          created_at?: string | null;
          encrypted_key: string;
          id?: never;
          provider: string;
          user_id: string;
        };
        Update: {
          created_at?: string | null;
          encrypted_key?: string;
          id?: never;
          provider?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      itinerary_items: {
        Row: {
          booking_status: string | null;
          created_at: string | null;
          currency: string | null;
          description: string | null;
          end_time: string | null;
          external_id: string | null;
          id: number;
          item_type: string;
          location: string | null;
          metadata: Json | null;
          price: number | null;
          start_time: string | null;
          title: string;
          trip_id: number;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          booking_status?: string | null;
          created_at?: string | null;
          currency?: string | null;
          description?: string | null;
          end_time?: string | null;
          external_id?: string | null;
          id?: never;
          item_type: string;
          location?: string | null;
          metadata?: Json | null;
          price?: number | null;
          start_time?: string | null;
          title: string;
          trip_id: number;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          booking_status?: string | null;
          created_at?: string | null;
          currency?: string | null;
          description?: string | null;
          end_time?: string | null;
          external_id?: string | null;
          id?: never;
          item_type?: string;
          location?: string | null;
          metadata?: Json | null;
          price?: number | null;
          start_time?: string | null;
          title?: string;
          trip_id?: number;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "itinerary_items_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      search_activities: {
        Row: {
          activity_type: string | null;
          created_at: string | null;
          destination: string;
          expires_at: string;
          id: number;
          query_hash: string;
          query_parameters: Json;
          results: Json;
          search_metadata: Json;
          source: string;
          user_id: string;
        };
        Insert: {
          activity_type?: string | null;
          created_at?: string | null;
          destination: string;
          expires_at: string;
          id?: never;
          query_hash: string;
          query_parameters: Json;
          results: Json;
          search_metadata?: Json;
          source: string;
          user_id: string;
        };
        Update: {
          activity_type?: string | null;
          created_at?: string | null;
          destination?: string;
          expires_at?: string;
          id?: never;
          query_hash?: string;
          query_parameters?: Json;
          results?: Json;
          search_metadata?: Json;
          source?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      search_destinations: {
        Row: {
          created_at: string | null;
          expires_at: string;
          id: number;
          query: string;
          query_hash: string;
          results: Json;
          search_metadata: Json;
          source: string;
          user_id: string;
        };
        Insert: {
          created_at?: string | null;
          expires_at: string;
          id?: never;
          query: string;
          query_hash: string;
          results: Json;
          search_metadata?: Json;
          source: string;
          user_id: string;
        };
        Update: {
          created_at?: string | null;
          expires_at?: string;
          id?: never;
          query?: string;
          query_hash?: string;
          results?: Json;
          search_metadata?: Json;
          source?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      search_flights: {
        Row: {
          cabin_class: string;
          created_at: string | null;
          departure_date: string;
          destination: string;
          expires_at: string;
          id: number;
          origin: string;
          passengers: number;
          query_hash: string;
          query_parameters: Json;
          results: Json;
          return_date: string | null;
          search_metadata: Json;
          source: string;
          user_id: string;
        };
        Insert: {
          cabin_class?: string;
          created_at?: string | null;
          departure_date: string;
          destination: string;
          expires_at: string;
          id?: never;
          origin: string;
          passengers?: number;
          query_hash: string;
          query_parameters: Json;
          results: Json;
          return_date?: string | null;
          search_metadata?: Json;
          source: string;
          user_id: string;
        };
        Update: {
          cabin_class?: string;
          created_at?: string | null;
          departure_date?: string;
          destination?: string;
          expires_at?: string;
          id?: never;
          origin?: string;
          passengers?: number;
          query_hash?: string;
          query_parameters?: Json;
          results?: Json;
          return_date?: string | null;
          search_metadata?: Json;
          source?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      search_hotels: {
        Row: {
          check_in_date: string;
          check_out_date: string;
          created_at: string | null;
          destination: string;
          expires_at: string;
          guests: number;
          id: number;
          query_hash: string;
          query_parameters: Json;
          results: Json;
          rooms: number;
          search_metadata: Json;
          source: string;
          user_id: string;
        };
        Insert: {
          check_in_date: string;
          check_out_date: string;
          created_at?: string | null;
          destination: string;
          expires_at: string;
          guests?: number;
          id?: never;
          query_hash: string;
          query_parameters: Json;
          results: Json;
          rooms?: number;
          search_metadata?: Json;
          source: string;
          user_id: string;
        };
        Update: {
          check_in_date?: string;
          check_out_date?: string;
          created_at?: string | null;
          destination?: string;
          expires_at?: string;
          guests?: number;
          id?: never;
          query_hash?: string;
          query_parameters?: Json;
          results?: Json;
          rooms?: number;
          search_metadata?: Json;
          source?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      trip_collaborators: {
        Row: {
          created_at: string | null;
          id: number;
          role: string;
          trip_id: number;
          user_id: string;
        };
        Insert: {
          created_at?: string | null;
          id?: never;
          role?: string;
          trip_id: number;
          user_id: string;
        };
        Update: {
          created_at?: string | null;
          id?: never;
          role?: string;
          trip_id?: number;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "trip_collaborators_trip_id_fkey";
            columns: ["trip_id"];
            isOneToOne: false;
            referencedRelation: "trips";
            referencedColumns: ["id"];
          },
        ];
      };
      trips: {
        Row: {
          budget: number;
          created_at: string | null;
          currency: string;
          destination: string;
          end_date: string;
          flexibility: Json | null;
          id: number;
          name: string;
          tags: string[] | null;
          search_metadata: Json | null;
          start_date: string;
          status: string;
          travelers: number;
          trip_type: string;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          budget: number;
          created_at?: string | null;
          currency?: string;
          destination: string;
          end_date: string;
          flexibility?: Json | null;
          id?: never;
          name: string;
          tags?: string[] | null;
          search_metadata?: Json | null;
          start_date: string;
          status?: string;
          travelers: number;
          trip_type?: string;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          budget?: number;
          created_at?: string | null;
          currency?: string;
          destination?: string;
          end_date?: string;
          flexibility?: Json | null;
          id?: never;
          name?: string;
          tags?: string[] | null;
          search_metadata?: Json | null;
          start_date?: string;
          status?: string;
          travelers?: number;
          trip_type?: string;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [];
      };
      user_settings: {
        Row: {
          allow_gateway_fallback: boolean;
          user_id: string;
        };
        Insert: {
          allow_gateway_fallback?: boolean;
          user_id: string;
        };
        Update: {
          allow_gateway_fallback?: boolean;
          user_id?: string;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      agent_config_upsert: {
        Args: {
          p_agent_type: string;
          p_config: Json;
          p_created_by: string;
          p_scope: string;
          p_summary?: string;
        };
        Returns: {
          config: Json;
          version_id: string;
        }[];
      };
      delete_user_api_key: {
        Args: { p_service: string; p_user_id: string };
        Returns: undefined;
      };
      delete_user_gateway_config: {
        Args: { p_user_id: string };
        Returns: undefined;
      };
      extract_trip_id_from_path: {
        Args: { file_path: string };
        Returns: number;
      };
      get_user_allow_gateway_fallback: {
        Args: { p_user_id: string };
        Returns: boolean;
      };
      get_user_api_key: {
        Args: { p_service: string; p_user_id: string };
        Returns: string;
      };
      get_user_gateway_base_url: {
        Args: { p_user_id: string };
        Returns: string;
      };
      insert_user_api_key: {
        Args: { p_api_key: string; p_service: string; p_user_id: string };
        Returns: string;
      };
      is_admin: { Args: never; Returns: boolean };
      match_accommodation_embeddings: {
        Args: {
          match_count?: number;
          match_threshold?: number;
          query_embedding: string;
        };
        Returns: {
          id: string;
          similarity: number;
        }[];
      };
      rt_is_session_member: { Args: never; Returns: boolean };
      rt_topic_prefix: { Args: never; Returns: string };
      rt_topic_suffix: { Args: never; Returns: string };
      touch_user_api_key: {
        Args: { p_service: string; p_user_id: string };
        Returns: undefined;
      };
      upsert_user_gateway_config: {
        Args: { p_base_url: string; p_user_id: string };
        Returns: undefined;
      };
      user_has_trip_access: {
        Args: { trip_id: number; user_id: string };
        Returns: boolean;
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
  storage: {
    Tables: {
      buckets: {
        Row: {
          allowed_mime_types: string[] | null;
          avif_autodetection: boolean | null;
          created_at: string | null;
          file_size_limit: number | null;
          id: string;
          name: string;
          owner: string | null;
          owner_id: string | null;
          public: boolean | null;
          type: Database["storage"]["Enums"]["buckettype"];
          updated_at: string | null;
        };
        Insert: {
          allowed_mime_types?: string[] | null;
          avif_autodetection?: boolean | null;
          created_at?: string | null;
          file_size_limit?: number | null;
          id: string;
          name: string;
          owner?: string | null;
          owner_id?: string | null;
          public?: boolean | null;
          type?: Database["storage"]["Enums"]["buckettype"];
          updated_at?: string | null;
        };
        Update: {
          allowed_mime_types?: string[] | null;
          avif_autodetection?: boolean | null;
          created_at?: string | null;
          file_size_limit?: number | null;
          id?: string;
          name?: string;
          owner?: string | null;
          owner_id?: string | null;
          public?: boolean | null;
          type?: Database["storage"]["Enums"]["buckettype"];
          updated_at?: string | null;
        };
        Relationships: [];
      };
      buckets_analytics: {
        Row: {
          created_at: string;
          format: string;
          id: string;
          type: Database["storage"]["Enums"]["buckettype"];
          updated_at: string;
        };
        Insert: {
          created_at?: string;
          format?: string;
          id: string;
          type?: Database["storage"]["Enums"]["buckettype"];
          updated_at?: string;
        };
        Update: {
          created_at?: string;
          format?: string;
          id?: string;
          type?: Database["storage"]["Enums"]["buckettype"];
          updated_at?: string;
        };
        Relationships: [];
      };
      iceberg_namespaces: {
        Row: {
          bucket_id: string;
          created_at: string;
          id: string;
          name: string;
          updated_at: string;
        };
        Insert: {
          bucket_id: string;
          created_at?: string;
          id?: string;
          name: string;
          updated_at?: string;
        };
        Update: {
          bucket_id?: string;
          created_at?: string;
          id?: string;
          name?: string;
          updated_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "iceberg_namespaces_bucket_id_fkey";
            columns: ["bucket_id"];
            isOneToOne: false;
            referencedRelation: "buckets_analytics";
            referencedColumns: ["id"];
          },
        ];
      };
      iceberg_tables: {
        Row: {
          bucket_id: string;
          created_at: string;
          id: string;
          location: string;
          name: string;
          namespace_id: string;
          updated_at: string;
        };
        Insert: {
          bucket_id: string;
          created_at?: string;
          id?: string;
          location: string;
          name: string;
          namespace_id: string;
          updated_at?: string;
        };
        Update: {
          bucket_id?: string;
          created_at?: string;
          id?: string;
          location?: string;
          name?: string;
          namespace_id?: string;
          updated_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "iceberg_tables_bucket_id_fkey";
            columns: ["bucket_id"];
            isOneToOne: false;
            referencedRelation: "buckets_analytics";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "iceberg_tables_namespace_id_fkey";
            columns: ["namespace_id"];
            isOneToOne: false;
            referencedRelation: "iceberg_namespaces";
            referencedColumns: ["id"];
          },
        ];
      };
      migrations: {
        Row: {
          executed_at: string | null;
          hash: string;
          id: number;
          name: string;
        };
        Insert: {
          executed_at?: string | null;
          hash: string;
          id: number;
          name: string;
        };
        Update: {
          executed_at?: string | null;
          hash?: string;
          id?: number;
          name?: string;
        };
        Relationships: [];
      };
      objects: {
        Row: {
          bucket_id: string | null;
          created_at: string | null;
          id: string;
          last_accessed_at: string | null;
          level: number | null;
          metadata: Json | null;
          name: string | null;
          owner: string | null;
          owner_id: string | null;
          path_tokens: string[] | null;
          updated_at: string | null;
          user_metadata: Json | null;
          version: string | null;
        };
        Insert: {
          bucket_id?: string | null;
          created_at?: string | null;
          id?: string;
          last_accessed_at?: string | null;
          level?: number | null;
          metadata?: Json | null;
          name?: string | null;
          owner?: string | null;
          owner_id?: string | null;
          path_tokens?: string[] | null;
          updated_at?: string | null;
          user_metadata?: Json | null;
          version?: string | null;
        };
        Update: {
          bucket_id?: string | null;
          created_at?: string | null;
          id?: string;
          last_accessed_at?: string | null;
          level?: number | null;
          metadata?: Json | null;
          name?: string | null;
          owner?: string | null;
          owner_id?: string | null;
          path_tokens?: string[] | null;
          updated_at?: string | null;
          user_metadata?: Json | null;
          version?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "objects_bucketId_fkey";
            columns: ["bucket_id"];
            isOneToOne: false;
            referencedRelation: "buckets";
            referencedColumns: ["id"];
          },
        ];
      };
      prefixes: {
        Row: {
          bucket_id: string;
          created_at: string | null;
          level: number;
          name: string;
          updated_at: string | null;
        };
        Insert: {
          bucket_id: string;
          created_at?: string | null;
          level?: number;
          name: string;
          updated_at?: string | null;
        };
        Update: {
          bucket_id?: string;
          created_at?: string | null;
          level?: number;
          name?: string;
          updated_at?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "prefixes_bucketId_fkey";
            columns: ["bucket_id"];
            isOneToOne: false;
            referencedRelation: "buckets";
            referencedColumns: ["id"];
          },
        ];
      };
      s3_multipart_uploads: {
        Row: {
          bucket_id: string;
          created_at: string;
          id: string;
          in_progress_size: number;
          key: string;
          owner_id: string | null;
          upload_signature: string;
          user_metadata: Json | null;
          version: string;
        };
        Insert: {
          bucket_id: string;
          created_at?: string;
          id: string;
          in_progress_size?: number;
          key: string;
          owner_id?: string | null;
          upload_signature: string;
          user_metadata?: Json | null;
          version: string;
        };
        Update: {
          bucket_id?: string;
          created_at?: string;
          id?: string;
          in_progress_size?: number;
          key?: string;
          owner_id?: string | null;
          upload_signature?: string;
          user_metadata?: Json | null;
          version?: string;
        };
        Relationships: [
          {
            foreignKeyName: "s3_multipart_uploads_bucket_id_fkey";
            columns: ["bucket_id"];
            isOneToOne: false;
            referencedRelation: "buckets";
            referencedColumns: ["id"];
          },
        ];
      };
      s3_multipart_uploads_parts: {
        Row: {
          bucket_id: string;
          created_at: string;
          etag: string;
          id: string;
          key: string;
          owner_id: string | null;
          part_number: number;
          size: number;
          upload_id: string;
          version: string;
        };
        Insert: {
          bucket_id: string;
          created_at?: string;
          etag: string;
          id?: string;
          key: string;
          owner_id?: string | null;
          part_number: number;
          size?: number;
          upload_id: string;
          version: string;
        };
        Update: {
          bucket_id?: string;
          created_at?: string;
          etag?: string;
          id?: string;
          key?: string;
          owner_id?: string | null;
          part_number?: number;
          size?: number;
          upload_id?: string;
          version?: string;
        };
        Relationships: [
          {
            foreignKeyName: "s3_multipart_uploads_parts_bucket_id_fkey";
            columns: ["bucket_id"];
            isOneToOne: false;
            referencedRelation: "buckets";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "s3_multipart_uploads_parts_upload_id_fkey";
            columns: ["upload_id"];
            isOneToOne: false;
            referencedRelation: "s3_multipart_uploads";
            referencedColumns: ["id"];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      add_prefixes: {
        Args: { _bucket_id: string; _name: string };
        Returns: undefined;
      };
      can_insert_object: {
        Args: { bucketid: string; metadata: Json; name: string; owner: string };
        Returns: undefined;
      };
      delete_leaf_prefixes: {
        Args: { bucket_ids: string[]; names: string[] };
        Returns: undefined;
      };
      delete_prefix: {
        Args: { _bucket_id: string; _name: string };
        Returns: boolean;
      };
      extension: { Args: { name: string }; Returns: string };
      filename: { Args: { name: string }; Returns: string };
      foldername: { Args: { name: string }; Returns: string[] };
      get_level: { Args: { name: string }; Returns: number };
      get_prefix: { Args: { name: string }; Returns: string };
      get_prefixes: { Args: { name: string }; Returns: string[] };
      get_size_by_bucket: {
        Args: never;
        Returns: {
          bucket_id: string;
          size: number;
        }[];
      };
      list_multipart_uploads_with_delimiter: {
        Args: {
          bucket_id: string;
          delimiter_param: string;
          max_keys?: number;
          next_key_token?: string;
          next_upload_token?: string;
          prefix_param: string;
        };
        Returns: {
          created_at: string;
          id: string;
          key: string;
        }[];
      };
      list_objects_with_delimiter: {
        Args: {
          bucket_id: string;
          delimiter_param: string;
          max_keys?: number;
          next_token?: string;
          prefix_param: string;
          start_after?: string;
        };
        Returns: {
          id: string;
          metadata: Json;
          name: string;
          updated_at: string;
        }[];
      };
      lock_top_prefixes: {
        Args: { bucket_ids: string[]; names: string[] };
        Returns: undefined;
      };
      operation: { Args: never; Returns: string };
      search: {
        Args: {
          bucketname: string;
          levels?: number;
          limits?: number;
          offsets?: number;
          prefix: string;
          search?: string;
          sortcolumn?: string;
          sortorder?: string;
        };
        Returns: {
          created_at: string;
          id: string;
          last_accessed_at: string;
          metadata: Json;
          name: string;
          updated_at: string;
        }[];
      };
      search_legacy_v1: {
        Args: {
          bucketname: string;
          levels?: number;
          limits?: number;
          offsets?: number;
          prefix: string;
          search?: string;
          sortcolumn?: string;
          sortorder?: string;
        };
        Returns: {
          created_at: string;
          id: string;
          last_accessed_at: string;
          metadata: Json;
          name: string;
          updated_at: string;
        }[];
      };
      search_v1_optimised: {
        Args: {
          bucketname: string;
          levels?: number;
          limits?: number;
          offsets?: number;
          prefix: string;
          search?: string;
          sortcolumn?: string;
          sortorder?: string;
        };
        Returns: {
          created_at: string;
          id: string;
          last_accessed_at: string;
          metadata: Json;
          name: string;
          updated_at: string;
        }[];
      };
      search_v2: {
        Args: {
          bucket_name: string;
          levels?: number;
          limits?: number;
          prefix: string;
          sort_column?: string;
          sort_column_after?: string;
          sort_order?: string;
          start_after?: string;
        };
        Returns: {
          created_at: string;
          id: string;
          key: string;
          last_accessed_at: string;
          metadata: Json;
          name: string;
          updated_at: string;
        }[];
      };
    };
    Enums: {
      buckettype: "STANDARD" | "ANALYTICS";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  auth: {
    Enums: {
      aal_level: ["aal1", "aal2", "aal3"],
      code_challenge_method: ["s256", "plain"],
      factor_status: ["unverified", "verified"],
      factor_type: ["totp", "webauthn", "phone"],
      oauth_authorization_status: ["pending", "approved", "denied", "expired"],
      oauth_client_type: ["public", "confidential"],
      oauth_registration_type: ["dynamic", "manual"],
      oauth_response_type: ["code"],
      one_time_token_type: [
        "confirmation_token",
        "reauthentication_token",
        "recovery_token",
        "email_change_token_new",
        "email_change_token_current",
        "phone_change_token",
      ],
    },
  },
  memories: {
    Enums: {},
  },
  public: {
    Enums: {},
  },
  storage: {
    Enums: {
      buckettype: ["STANDARD", "ANALYTICS"],
    },
  },
} as const;

// Helper type aliases for ergonomic access to generated helpers
type PublicTables = keyof DefaultSchema["Tables"];
type SchemaName = keyof DatabaseWithoutInternals;

export type InsertTables<TableName extends PublicTables> =
  DefaultSchema["Tables"][TableName] extends { Insert: infer I } ? I : never;
export type InsertTablesInSchema<
  Schema extends SchemaName,
  TableName extends keyof DatabaseWithoutInternals[Schema]["Tables"],
> = DatabaseWithoutInternals[Schema]["Tables"][TableName] extends { Insert: infer I }
  ? I
  : never;

export type UpdateTables<TableName extends PublicTables> =
  DefaultSchema["Tables"][TableName] extends { Update: infer U } ? U : never;
export type UpdateTablesInSchema<
  Schema extends SchemaName,
  TableName extends keyof DatabaseWithoutInternals[Schema]["Tables"],
> = DatabaseWithoutInternals[Schema]["Tables"][TableName] extends { Update: infer U }
  ? U
  : never;

// Convenience aliases for common tables
export type Trip = Tables<"trips">;
export type TripInsert = InsertTables<"trips">;
export type TripUpdate = UpdateTables<"trips">;

export type Accommodation = Tables<"accommodations">;
export type AccommodationInsert = InsertTables<"accommodations">;
export type AccommodationUpdate = UpdateTables<"accommodations">;

export type FileAttachment = Tables<"file_attachments">;
export type FileAttachmentInsert = InsertTables<"file_attachments">;
export type FileAttachmentUpdate = UpdateTables<"file_attachments">;
export type UploadStatus = FileAttachment["upload_status"];
export type VirusScanStatus = FileAttachment["virus_scan_status"];

export type ChatSession = Tables<"chat_sessions">;
export type ChatSessionInsert = InsertTables<"chat_sessions">;
export type ChatMessage = Tables<"chat_messages">;
export type ChatMessageInsert = InsertTables<"chat_messages">;
export type ChatToolCall = Tables<"chat_tool_calls">;
export type ChatToolCallInsert = InsertTables<"chat_tool_calls">;
export type ChatRole = ChatMessage["role"];

export type MemorySession = Tables<{ schema: "memories" }, "sessions">;
export type MemorySessionInsert = InsertTablesInSchema<"memories", "sessions">;
export type MemorySessionUpdate = UpdateTablesInSchema<"memories", "sessions">;
export type MemoryTurn = Tables<{ schema: "memories" }, "turns">;
export type MemoryTurnInsert = InsertTablesInSchema<"memories", "turns">;
export type MemoryTurnUpdate = UpdateTablesInSchema<"memories", "turns">;
