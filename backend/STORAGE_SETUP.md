# Storage Service Setup Guide

## Overview
The ConsultEase application uses Supabase Storage for file uploads. This guide helps you set up and troubleshoot the storage service.

## Prerequisites
1. A Supabase project with Storage enabled
2. Service role key with storage permissions
3. A storage bucket named "contract-documents"

## Environment Variables
Create a `.env` file in the backend directory with:

```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

## Setup Steps

### 1. Create Storage Bucket
In your Supabase dashboard:
1. Go to Storage section
2. Create a new bucket named "contract-documents"
3. Set it to private (recommended for contracts)
4. Enable RLS (Row Level Security)

### 2. Set Storage Policies
Add this policy to allow authenticated uploads:

```sql
CREATE POLICY "Allow authenticated uploads" ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'contract-documents');
```

### 3. Test Configuration
Run the test script to verify setup:

```bash
cd backend
python test_storage.py
```

## Troubleshooting

### Common Errors

#### "UploadResponse object has no attribute 'get'"
- **Cause**: Supabase storage response format mismatch
- **Solution**: The code has been updated to handle this. Check environment variables are set correctly.

#### "Storage service configuration error"
- **Cause**: Missing or invalid environment variables
- **Solution**: Verify SUPABASE_URL and SUPABASE_SERVICE_KEY are set correctly

#### "Upload failed: Upload failed"
- **Cause**: Generic upload failure
- **Solution**: Check Supabase logs, verify bucket exists, check file size limits

### Debug Steps
1. Check environment variables are set
2. Verify Supabase project is accessible
3. Check storage bucket exists and has correct permissions
4. Review server logs for detailed error messages
5. Test with the storage test script

## File Upload Limits
- **File Types**: PDF, DOC, DOCX only
- **Max Size**: 10MB
- **Storage**: Supabase Storage with automatic cleanup

## Security Notes
- Service role key has full access - keep it secure
- Files are stored in private buckets
- Consider implementing user-specific access controls
- Regular audit of uploaded files recommended
