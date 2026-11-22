import React, { useState, useEffect, useCallback } from "react";
import {
  Star,
  MessageSquare,
  Flag,
  Trash2,
  Edit3,
  Check,
  AlertCircle,
  Loader2,
  User,
} from "lucide-react";
import {
  fetchGameReviews,
  submitGameReview,
  deleteGameReview,
  reportGameReview,
} from "./services/libraryService.js";
import { useLibrary } from "./context/LibraryContext.jsx";

export default function ReviewSection({ appid, onRequireLogin }) {
  const { libraryMap, setLocalStatus, refreshLibrary } = useLibrary();
  const currentStatus = libraryMap[appid] || {};

  const [reviewData, setReviewData] = useState({
    average_rating: null,
    total_ratings: 0,
    total_reviews: 0,
    reviews: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Review Form State
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedRating, setSelectedRating] = useState(currentStatus.rating || 10);
  const [commentText, setCommentText] = useState(currentStatus.review || "");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Reporting State
  const [reportingId, setReportingId] = useState(null);
  const [reportedIds, setReportedIds] = useState(new Set());

  // Load reviews for this game
  const loadReviews = useCallback(async () => {
    if (!appid) return;
    setLoading(true);
    try {
      const data = await fetchGameReviews(appid);
      setReviewData(data);
      setError("");
    } catch (err) {
      console.error("Failed to fetch reviews:", err);
      setError("Unable to load community reviews at this time.");
    } finally {
      setLoading(false);
    }
  }, [appid]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  // Sync form inputs when game or user status changes
  useEffect(() => {
    if (currentStatus.rating) {
      setSelectedRating(currentStatus.rating);
    }
    if (currentStatus.review) {
      setCommentText(currentStatus.review);
    }
  }, [currentStatus.rating, currentStatus.review]);

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    if (!selectedRating || selectedRating < 1 || selectedRating > 10) {
      setFormError("Please select a rating between 1 and 10.");
      return;
    }
    setSubmitting(true);
    setFormError("");
    try {
      const updatedState = await submitGameReview(
        appid,
        Number(selectedRating),
        commentText.trim() || null
      );
      // Update local state in LibraryContext
      setLocalStatus(appid, {
        rating: updatedState.rating,
        review: updatedState.review,
        already_played: true,
      });
      setIsFormOpen(false);
      await loadReviews();
      refreshLibrary();
    } catch (err) {
      setFormError(err.message || "Failed to submit review.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteReview = async () => {
    if (!window.confirm("Are you sure you want to delete your review?")) return;
    setSubmitting(true);
    try {
      await deleteGameReview(appid);
      setLocalStatus(appid, {
        rating: null,
        review: null,
      });
      setSelectedRating(10);
      setCommentText("");
      setIsFormOpen(false);
      await loadReviews();
      refreshLibrary();
    } catch (err) {
      alert(err.message || "Failed to delete review.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReport = async (review) => {
    const reason = window.prompt("Reason for reporting this review (e.g. spam, offensive):");
    if (!reason) return;
    try {
      await reportGameReview(appid, review.user_id, reason);
      setReportedIds((prev) => new Set([...prev, review.id]));
      alert("Review has been reported to moderators. Thank you!");
      await loadReviews();
    } catch (err) {
      alert(err.message || "Failed to report review.");
    }
  };

  return (
    <section className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-6 sm:p-8 backdrop-blur-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <Star className="h-5 w-5 fill-amber-400 text-amber-400" />
            <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
              Community Ratings & Reviews
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Player ratings from 1 to 10. Strictly independent from RigCheck hardware compatibility scores.
          </p>
        </div>

        {/* Rating Score Card */}
        <div className="flex items-center gap-3 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-2.5 backdrop-blur-sm self-start sm:self-auto">
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black text-amber-400">
              {reviewData.average_rating !== null ? reviewData.average_rating : "--"}
            </span>
            <span className="text-sm font-bold text-amber-400/70">/10</span>
          </div>
          <div className="h-6 w-px bg-amber-400/20" />
          <div className="text-[11px] text-slate-400 leading-tight">
            <span className="block font-bold text-white">
              {reviewData.total_ratings} {reviewData.total_ratings === 1 ? "Rating" : "Ratings"}
            </span>
            <span>{reviewData.total_reviews} with written review</span>
          </div>
        </div>
      </div>

      {/* Action Banner: User Review Status or Prompt */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400/10 text-cyan-400">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">
              {currentStatus.rating ? "You Reviewed This Game" : "Played this game?"}
            </h4>
            <p className="text-xs text-slate-400">
              {currentStatus.rating
                ? `Your current rating: ${currentStatus.rating}/10`
                : "Mark as Played and share your rating and experience with the community."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {currentStatus.rating ? (
            <>
              <button
                type="button"
                onClick={() => setIsFormOpen(!isFormOpen)}
                className="flex items-center gap-1.5 rounded-xl border border-cyan-400/40 bg-cyan-950/40 px-3.5 py-2 text-xs font-bold text-cyan-300 hover:bg-cyan-900/40 transition-all"
              >
                <Edit3 className="h-3.5 w-3.5" />
                <span>{isFormOpen ? "Cancel Edit" : "Edit Review"}</span>
              </button>
              <button
                type="button"
                onClick={handleDeleteReview}
                disabled={submitting}
                className="flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-950/30 px-3 py-2 text-xs font-bold text-rose-300 hover:bg-rose-900/40 transition-all"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete</span>
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setIsFormOpen(!isFormOpen)}
              className="flex items-center gap-1.5 rounded-xl border border-amber-400/50 bg-amber-500/20 px-4 py-2 text-xs font-bold text-amber-300 hover:bg-amber-500/30 shadow-[0_0_15px_rgba(251,191,36,0.2)] transition-all"
            >
              <Star className="h-3.5 w-3.5 fill-amber-400" />
              <span>{isFormOpen ? "Close Form" : "Rate & Review"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Review Submission Form */}
      {isFormOpen && (
        <form
          onSubmit={handleSubmitReview}
          className="rounded-2xl border border-cyan-400/30 bg-slate-900/70 p-5 space-y-4 animate-fadeIn"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-cyan-400">
              {currentStatus.rating ? "Update Your Review" : "Rate This Game"}
            </h3>
            <span className="text-xs font-black text-amber-400">
              Score: {selectedRating}/10
            </span>
          </div>

          {formError && (
            <div className="flex items-center gap-2 rounded-xl bg-rose-500/10 border border-rose-500/30 p-2.5 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          {/* Rating 1-10 Selector */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">
              Select Score (1 = Terrible, 10 = Masterpiece)
            </label>
            <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setSelectedRating(num)}
                  className={`h-10 rounded-xl font-black text-xs transition-all ${
                    selectedRating === num
                      ? "border border-amber-400 bg-amber-500 text-slate-950 shadow-[0_0_15px_rgba(251,191,36,0.5)] scale-105"
                      : "border border-slate-700 bg-slate-950/80 text-slate-300 hover:border-amber-400/40 hover:text-white"
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
          </div>

          {/* Comment Textarea */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-300">
                Written Review (Optional)
              </label>
              <span className="text-[10px] text-slate-500">
                {commentText.length}/1000
              </span>
            </div>
            <textarea
              rows={3}
              maxLength={1000}
              placeholder="What did you think of the gameplay, story, performance, or mechanics?"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950/70 p-3 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/30 transition-colors"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={() => setIsFormOpen(false)}
              className="rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2 text-xs font-bold text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 disabled:opacity-60 transition-all shadow-[0_0_15px_rgba(34,211,238,0.3)]"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Check className="h-3.5 w-3.5" />
                  <span>{currentStatus.rating ? "Update Review" : "Publish Review"}</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Public Reviews List */}
      <div className="space-y-4 pt-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Player Reviews ({reviewData.reviews.length})
        </h3>

        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-center text-xs text-slate-400">
            {error}
          </div>
        ) : reviewData.reviews.length === 0 ? (
          <div className="rounded-2xl border border-slate-800/80 bg-slate-950/40 p-8 text-center">
            <MessageSquare className="mx-auto mb-2 h-8 w-8 text-slate-600" />
            <p className="text-xs font-medium text-slate-400">
              No written reviews yet for this game. Be the first to share your thoughts!
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {reviewData.reviews.map((rev) => {
              const isReported = reportedIds.has(rev.id) || rev.report_count > 0;
              return (
                <div
                  key={rev.id || rev.user_id}
                  className="rounded-2xl border border-slate-800/80 bg-slate-900/30 p-4 transition-all hover:border-slate-700/80"
                >
                  <div className="flex items-start justify-between gap-3">
                    {/* User Info */}
                    <div className="flex items-center gap-2.5">
                      {rev.user_avatar ? (
                        <img
                          src={rev.user_avatar}
                          alt={rev.user_display_name}
                          className="h-8 w-8 rounded-full border border-cyan-400/40 object-cover"
                        />
                      ) : (
                        <div className="grid h-8 w-8 place-items-center rounded-full border border-slate-700 bg-slate-800 text-xs font-bold text-cyan-300">
                          {(rev.user_display_name || "G")[0].toUpperCase()}
                        </div>
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white">
                            {rev.user_display_name}
                          </span>
                          {rev.is_owner && (
                            <span className="rounded-full bg-cyan-950/80 border border-cyan-400/30 px-2 py-0.5 text-[9px] font-bold text-cyan-300">
                              You
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500">
                          {new Date(rev.created_at).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      </div>
                    </div>

                    {/* Rating Badge & Report */}
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 rounded-full border border-amber-400/30 bg-amber-500/15 px-2.5 py-1 text-xs font-black text-amber-300 shadow-[0_0_8px_rgba(251,191,36,0.2)]">
                        <Star className="h-3 w-3 fill-amber-400" />
                        {rev.rating}/10
                      </span>

                      {!rev.is_owner && (
                        <button
                          type="button"
                          onClick={() => handleReport(rev)}
                          disabled={isReported}
                          title={isReported ? "Reported" : "Report review"}
                          className={`grid h-7 w-7 place-items-center rounded-lg transition-colors ${
                            isReported
                              ? "text-rose-400 cursor-default"
                              : "text-slate-500 hover:bg-slate-800 hover:text-slate-300"
                          }`}
                        >
                          <Flag className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Comment */}
                  {rev.comment && (
                    <p className="mt-3 text-xs leading-relaxed text-slate-300">
                      {rev.comment}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
