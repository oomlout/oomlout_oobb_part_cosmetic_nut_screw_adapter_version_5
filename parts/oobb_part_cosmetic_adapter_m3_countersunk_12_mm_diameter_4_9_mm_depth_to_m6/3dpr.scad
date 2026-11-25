$fn = 100;

translate([0, 0, 1.9]) rotate([180, 0, 0])
difference() {
    union() {
        cylinder(h=1.9, d=12);
        translate([0, 0, -3]) cylinder(h=3, d=5.75);
    }
    translate([0, 0, 0]) cylinder(h=1.9, r1=1.8, r2=3.6);
    translate([0, 0, -4]) cylinder(h=6.9, r=1.8);
}
