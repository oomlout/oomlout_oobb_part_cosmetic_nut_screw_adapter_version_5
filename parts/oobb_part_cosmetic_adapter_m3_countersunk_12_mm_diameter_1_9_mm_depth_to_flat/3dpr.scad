$fn = 100;

difference() {
    cylinder(h=1.9, d=12);
    translate([0, 0, 0])
        cylinder(h=1.9, r1=1.8, r2=3.6);
    translate([0, 0, -1])
        cylinder(h=3.9, r=1.8);
}
