import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft, Navigation, Zap, Clock } from 'lucide-react-native';
import { mockStations } from '../data/mockData';
import { theme, webStyles } from '../theme';

export default function ResultsScreen({ navigation }: any) {
  const top = mockStations.find((s) => s.isCheapest);
  const alternatives = mockStations.filter((s) => !s.isCheapest);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <ChevronLeft color={theme.colors.text} size={28} />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>Charging Options</Text>
        </View>

        {/* Top Recommendation */}
        {top && (
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>TOP RECOMMENDATION</Text>
            <TouchableOpacity
              style={[styles.topCard, webStyles.neonGlow]}
              onPress={() => navigation.navigate('StationDetails')}
              activeOpacity={0.85}
            >
              <View style={styles.topCardHeader}>
                <View style={{ flex: 1 }}>
                  <View style={styles.badgeRow}>
                    <Zap color={theme.colors.primary} fill={theme.colors.primary} size={12} />
                    <Text style={styles.badgeText}>CHEAPEST OPTION</Text>
                  </View>
                  <Text style={styles.stationName}>{top.name}</Text>
                  <Text style={styles.stationSub}>{top.provider} · {top.distance} away</Text>
                </View>
                <Text style={styles.price}>EGP {top.totalPrice}</Text>
              </View>
              <View style={styles.statsRow}>
                <View style={styles.statBox}>
                  <Clock color={theme.colors.textMuted} size={20} />
                  <View>
                    <Text style={styles.statValue}>{top.totalTime}</Text>
                    <Text style={styles.statSub}>TOTAL TIME</Text>
                  </View>
                </View>
                <View style={styles.statBox}>
                  <Zap color={theme.colors.textMuted} size={20} />
                  <View>
                    <Text style={styles.statValue}>{top.power}</Text>
                    <Text style={styles.statSub}>SPEED</Text>
                  </View>
                </View>
              </View>
            </TouchableOpacity>
          </View>
        )}

        {/* Alternatives */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>ALTERNATIVES</Text>
          {alternatives.map((s) => (
            <TouchableOpacity
              key={s.id}
              style={styles.altCard}
              onPress={() => navigation.navigate('StationDetails')}
              activeOpacity={0.85}
            >
              <View style={styles.altHeader}>
                <View>
                  {s.isFastest && <Text style={styles.fastestLabel}>FASTEST OPTION</Text>}
                  <Text style={styles.altName}>{s.name}</Text>
                </View>
                <Text style={styles.altPrice}>EGP {s.totalPrice}</Text>
              </View>
              <View style={styles.altMeta}>
                <View style={styles.metaItem}>
                  <Clock color={theme.colors.textMuted} size={13} />
                  <Text style={styles.metaText}>{s.totalTime}</Text>
                </View>
                <View style={styles.dot} />
                <View style={styles.metaItem}>
                  <Navigation color={theme.colors.textMuted} fill={theme.colors.textMuted} size={13} />
                  <Text style={styles.metaText}>{s.distance}</Text>
                </View>
                <View style={styles.dot} />
                <View style={styles.metaItem}>
                  <Zap color={theme.colors.primary} fill={theme.colors.primary} size={13} />
                  <Text style={styles.metaText}>{s.power}</Text>
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.colors.background },
  container: { paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: 40 },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md, marginBottom: theme.spacing.xl },
  backBtn: { padding: 4 },
  pageTitle: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold' },
  section: { marginBottom: theme.spacing.xl },
  sectionLabel: {
    color: theme.colors.textMuted, fontSize: 10, fontWeight: 'bold',
    letterSpacing: 2, marginBottom: theme.spacing.md,
  },
  topCard: {
    ...theme.neonGlow,
    backgroundColor: '#121416',
    borderRadius: theme.radii.xxl,
    borderWidth: 2,
    borderColor: theme.colors.primary,
    padding: theme.spacing.lg,
  },
  topCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: theme.spacing.md, marginBottom: theme.spacing.lg },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
  badgeText: { color: theme.colors.primary, fontSize: 10, fontWeight: 'bold', letterSpacing: 1 },
  stationName: { color: theme.colors.text, fontSize: 20, fontWeight: 'bold', marginBottom: 2 },
  stationSub: { color: theme.colors.textMuted, fontSize: 12 },
  price: { color: theme.colors.text, fontSize: 24, fontWeight: 'bold' },
  statsRow: { flexDirection: 'row', gap: theme.spacing.md },
  statBox: {
    flex: 1, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: theme.radii.xl,
    padding: theme.spacing.md, flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm,
  },
  statValue: { color: theme.colors.text, fontSize: 14, fontWeight: 'bold' },
  statSub: { color: theme.colors.textMuted, fontSize: 9, fontWeight: 'bold', letterSpacing: 1 },
  altCard: {
    backgroundColor: theme.colors.surfaceLight,
    borderRadius: theme.radii.xl,
    padding: theme.spacing.lg,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: '#222426',
  },
  altHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: theme.spacing.sm },
  fastestLabel: { color: theme.colors.primary, fontSize: 9, fontWeight: 'bold', letterSpacing: 1, marginBottom: 2 },
  altName: { color: theme.colors.text, fontSize: 15, fontWeight: 'bold' },
  altPrice: { color: '#d1d5db', fontSize: 14, fontWeight: 'bold' },
  altMeta: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { color: theme.colors.textMuted, fontSize: 12, fontWeight: '500' },
  dot: { width: 4, height: 4, borderRadius: 2, backgroundColor: '#374151' },
});
