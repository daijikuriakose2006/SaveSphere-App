# SaveSphere App: Supabase Migration Guide

This guide outlines the steps necessary to complete the migration from Django's default database to Supabase.

## Prerequisites

1. A Supabase account and project set up at [https://supabase.com](https://supabase.com)
2. Python 3.8+ and pip installed
3. Virtual environment created and activated
4. Required dependencies installed: `pip install -r requirements.txt`

## Configuration

1. Update the `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=https://your-supabase-project-url.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_BUCKET=savesphere-files
   ```

2. In your Supabase project, create the following tables:

### Tables

#### profiles
- `id` (uuid, primary key)
- `username` (text)
- `bio` (text)
- `profile_picture_url` (text)
- `storage_quota` (bigint, default: 104857600)
- `storage_used` (bigint, default: 0)
- `is_blocked_upload` (boolean, default: false)
- `created_at` (timestamp with timezone)
- `updated_at` (timestamp with timezone)

#### albums
- `id` (uuid, primary key)
- `user_id` (uuid, references auth.users.id)
- `name` (text)
- `description` (text)
- `is_public` (boolean, default: false)
- `created_at` (timestamp with timezone)
- `updated_at` (timestamp with timezone)

#### media
- `id` (uuid, primary key)
- `user_id` (uuid, references auth.users.id)
- `album_id` (uuid, references albums.id, nullable)
- `title` (text)
- `description` (text)
- `media_type` (text)
- `file_url` (text)
- `file_size` (bigint)
- `storage_path` (text)
- `is_public` (boolean, default: false)
- `created_at` (timestamp with timezone)
- `updated_at` (timestamp with timezone)

#### favorites
- `id` (uuid, primary key)
- `user_id` (uuid, references auth.users.id)
- `media_id` (uuid, references media.id)
- `created_at` (timestamp with timezone)

### Storage Buckets

Create a storage bucket named `savesphere-files` with the following configuration:
- Public access: Enabled (for file access)
- File size limit: 100MB

## RLS (Row Level Security) Policies

Set up the following RLS policies for each table:

### profiles
- Allow users to read their own profiles
- Allow authenticated users to update their own profiles
- Only allow admins to delete profiles

### albums
- Allow users to read their own albums and public albums
- Allow users to create/update/delete their own albums

### media
- Allow users to read their own media and public media
- Allow users to create/update/delete their own media

### favorites
- Allow users to read their own favorites
- Allow users to create/delete their own favorites

## Data Migration

To migrate existing data from SQLite to Supabase:

1. Run the provided migration script:
   ```
   python migrate_to_supabase.py
   ```

   This script will:
   - Create users in Supabase Auth from Django users
   - Migrate user profiles to Supabase
   - Upload media files to Supabase Storage
   - Migrate albums, media records, and favorites

## Using The New System

The application now uses Supabase for:
- User authentication (registration, login, password reset)
- Data storage (profiles, albums, media, favorites)
- File storage (media files, profile pictures)

The Django models are still defined for compatibility with the Django admin, but all database interactions now go through the Supabase API.

## Troubleshooting

- If authentication issues occur, check that your Supabase URL and API key are correct
- For file upload issues, verify that the storage bucket is properly configured
- For permission errors, check the RLS policies in your Supabase project

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Python Supabase Client](https://github.com/supabase-community/supabase-py)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth) 